from dataclasses import dataclass, asdict
from typing import Optional, Literal
import pandas as pd
import numpy as np
from datetime import datetime

from app.services.stock_service import fetch_stock_data, calculate_indicators
from app.services.relative_strength import calculate_relative_strength
from app.services.market_service import get_sector_flow, get_sector_performance
from app.database.foreign_flow_models import get_accumulation_status, get_foreign_flow


SECTOR_MAP = {
    "BBCA": "Financials", "BBRI": "Financials", "BMRI": "Financials", "BBNI": "Financials",
    "TLKM": "Telecommunication", "EXCL": "Telecommunication", "TOWR": "Telecommunication",
    "ASII": "Automotive", "UNVR": "Consumer Goods", "HMSP": "Consumer Goods",
    "GGRM": "Consumer Goods", "INDF": "Consumer Goods", "ICBP": "Consumer Goods",
    "KLBF": "Healthcare", "CPIN": "Consumer Goods",
    "ADRO": "Energy", "ITMG": "Energy", "PTBA": "Energy", "MEDC": "Energy",
    "PGAS": "Energy",
    "SMGR": "Infrastructure", "INTP": "Infrastructure", "JSMR": "Infrastructure",
    "AKRA": "Energy",
    "SMMA": "Financials",
    "EXCL": "Telecommunication",
}

StrategyType = Literal["swing", "day_trade", "long_term"]
RiskLevel = Literal["low", "moderate", "high"]


@dataclass
class ScoringComponent:
    name: str
    weight: float
    score: float
    weighted_score: float
    reason: str
    data_source: str


@dataclass
class ScoringResult:
    stock_code: str
    strategy: StrategyType
    risk_level: RiskLevel
    components: list[ScoringComponent]
    total_score: float
    recommendation: str
    confidence: float
    summary: str
    risks: list[str]
    catalysts: list[str]
    last_updated: str


class ScoringEngine:

    def _clamp(self, score: float) -> float:
        return max(0.0, min(100.0, score))

    def score_technical(self, df: pd.DataFrame) -> ScoringComponent:
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        score = 50.0
        reasons = []

        rsi = latest.get("RSI")
        if pd.notna(rsi):
            if 30 <= rsi <= 70:
                score += 20
                reasons.append("RSI normal")
            elif rsi < 30:
                macd = latest.get("MACD")
                macd_signal = latest.get("MACD_Signal")
                if pd.notna(macd) and pd.notna(macd_signal) and macd > macd_signal:
                    score += 40
                    reasons.append("RSI oversold + MACD golden cross")
            elif rsi > 70:
                score -= 20
                reasons.append("RSI overbought")

        macd = latest.get("MACD")
        macd_signal = latest.get("MACD_Signal")
        macd_hist = latest.get("MACD_Hist")
        if pd.notna(macd) and pd.notna(macd_signal):
            if macd > macd_signal and pd.notna(macd_hist) and macd_hist > 0:
                score += 20
                reasons.append("MACD bullish + histogram positive")
            prev_macd = prev.get("MACD")
            prev_macd_signal = prev.get("MACD_Signal")
            if pd.notna(prev_macd) and pd.notna(prev_macd_signal):
                if macd > macd_signal and prev_macd <= prev_macd_signal:
                    score += 30
                    reasons.append("MACD golden cross new")
                elif macd < macd_signal and prev_macd >= prev_macd_signal:
                    score -= 30
                    reasons.append("MACD death cross new")

        close = latest.get("Close")
        ma20 = latest.get("MA20")
        ma50 = latest.get("MA50")
        if pd.notna(close) and pd.notna(ma20) and pd.notna(ma50):
            if close > ma20 > ma50:
                score += 20
                reasons.append("Price > MA20 > MA50 (bullish alignment)")
            elif close < ma20 < ma50:
                score -= 20
                reasons.append("Price < MA20 < MA50 (bearish alignment)")

        volume = latest.get("Volume")
        volume_ma = latest.get("Volume_MA")
        if pd.notna(volume) and pd.notna(volume_ma) and volume_ma > 0:
            if volume > 1.5 * volume_ma:
                score += 15
                reasons.append("Volume spike > 1.5x average")

        close_price = latest.get("Close")
        s1 = latest.get("S1")
        r1 = latest.get("R1")
        if pd.notna(close_price) and pd.notna(s1) and s1 > 0:
            if abs(close_price - s1) / close_price < 0.02:
                score += 10
                reasons.append("Near support")
        if pd.notna(close_price) and pd.notna(r1) and r1 > 0:
            if abs(close_price - r1) / close_price < 0.02:
                score -= 10
                reasons.append("Near resistance")

        score = self._clamp(score)
        reason = "; ".join(reasons) if reasons else "Neutral technical outlook"
        return ScoringComponent(
            name="Technical",
            weight=0.0,
            score=score,
            weighted_score=0.0,
            reason=reason,
            data_source="Yahoo Finance",
        )

    def score_foreign_flow(self, stock_code: str) -> ScoringComponent:
        flow_data = get_foreign_flow(stock_code, days=5)
        if not flow_data:
            return ScoringComponent(
                name="Foreign Flow",
                weight=0.0,
                score=0.0,
                weighted_score=0.0,
                reason="No foreign flow data available",
                data_source="Database",
            )

        score = 50.0
        reasons = []

        accum = get_accumulation_status(stock_code)
        if accum is not None:
            accum_days = accum.get("accumulation_days", 0)
            distrib_days = accum.get("distribution_days", 0)
            strength = accum.get("strength", "weak")
            if accum_days >= 5 and strength == "strong":
                score += 60
                reasons.append(f"Strong accumulation {accum_days} days")
            elif accum_days >= 3:
                score += 40
                reasons.append(f"Accumulating {accum_days} days")
            if distrib_days >= 5 and strength == "strong":
                score -= 50
                reasons.append(f"Strong distribution {distrib_days} days")
            elif distrib_days >= 3:
                score -= 30
                reasons.append(f"Distributing {distrib_days} days")

        net_flow = sum(row.get("foreign_net", 0) for row in flow_data)
        if net_flow > 0:
            score += 20
            reasons.append("Net foreign inflow last 5 days")
        else:
            score -= 20
            reasons.append("Net foreign outflow last 5 days")

        score = self._clamp(score)
        reason = "; ".join(reasons) if reasons else "Neutral foreign flow"
        return ScoringComponent(
            name="Foreign Flow",
            weight=0.0,
            score=score,
            weighted_score=0.0,
            reason=reason,
            data_source="Database",
        )

    def score_accumulation(self, stock_code: str) -> ScoringComponent:
        accum = get_accumulation_status(stock_code)
        if accum is None:
            return ScoringComponent(
                name="Accumulation",
                weight=0.0,
                score=0.0,
                weighted_score=0.0,
                reason="No accumulation data available",
                data_source="Database",
            )

        score = 50.0
        reasons = []
        accum_days = accum.get("accumulation_days", 0)
        distrib_days = accum.get("distribution_days", 0)
        strength = accum.get("strength", "weak")

        if accum_days >= 5:
            score += 50
            reasons.append(f"Accumulation {accum_days} days")
        elif accum_days >= 3:
            score += 30
            reasons.append(f"Accumulation {accum_days} days")

        if distrib_days >= 5:
            score -= 50
            reasons.append(f"Distribution {distrib_days} days")
        elif distrib_days >= 3:
            score -= 30
            reasons.append(f"Distribution {distrib_days} days")

        if strength == "strong":
            score += 15
            reasons.append("Strong accumulation strength")

        score = self._clamp(score)
        reason = "; ".join(reasons) if reasons else "Neutral accumulation"
        return ScoringComponent(
            name="Accumulation",
            weight=0.0,
            score=score,
            weighted_score=0.0,
            reason=reason,
            data_source="Database",
        )

    def score_relative_strength(self, stock_code: str) -> ScoringComponent:
        rs_data = calculate_relative_strength(stock_code)
        if rs_data is None:
            return ScoringComponent(
                name="Relative Strength",
                weight=0.0,
                score=0.0,
                weighted_score=0.0,
                reason="No relative strength data available",
                data_source="Yahoo Finance",
            )

        score = 50.0
        rs_value = rs_data.get("rs_value", 0)
        reasons = []

        if rs_value > 10:
            score += 50
            reasons.append(f"RS {rs_value} > 10 (strong outperformance)")
        elif rs_value > 5:
            score += 30
            reasons.append(f"RS {rs_value} > 5 (outperforming)")
        elif rs_value > 2:
            score += 15
            reasons.append(f"RS {rs_value} > 2 (slight outperformance)")
        elif rs_value < -10:
            score -= 50
            reasons.append(f"RS {rs_value} < -10 (strong underperformance)")
        elif rs_value < -5:
            score -= 30
            reasons.append(f"RS {rs_value} < -5 (underperforming)")
        elif rs_value < -2:
            score -= 15
            reasons.append(f"RS {rs_value} < -2 (slight underperformance)")
        else:
            score += 5
            reasons.append(f"RS {rs_value} (neutral)")

        score = self._clamp(score)
        reason = "; ".join(reasons)
        return ScoringComponent(
            name="Relative Strength",
            weight=0.0,
            score=score,
            weighted_score=0.0,
            reason=reason,
            data_source="Yahoo Finance",
        )

    def score_sector(self, stock_code: str) -> ScoringComponent:
        code = stock_code.upper().replace(".JK", "")
        sector = SECTOR_MAP.get(code)
        if sector is None:
            return ScoringComponent(
                name="Sector",
                weight=0.0,
                score=50.0,
                weighted_score=0.0,
                reason="Unknown sector",
                data_source="Market Service",
            )

        try:
            flow_data = get_sector_flow()
        except NameError:
            get_sector_performance()
            flow_data = get_sector_flow()

        score = 50.0
        reasons = []

        inflow_sectors = flow_data.get("inflow_sectors", [])
        outflow_sectors = flow_data.get("outflow_sectors", [])
        top_sector = flow_data.get("top_sector")
        worst_sector = flow_data.get("worst_sector")

        if sector in inflow_sectors:
            score += 30
            reasons.append(f"{sector} sector in inflow")
        if sector == top_sector:
            score += 40
            reasons.append(f"{sector} is top performing sector")
        if sector in outflow_sectors:
            score -= 20
            reasons.append(f"{sector} sector in outflow")
        if sector == worst_sector:
            score -= 30
            reasons.append(f"{sector} is worst performing sector")
        if not reasons:
            score += 5
            reasons.append(f"{sector} sector neutral")

        score = self._clamp(score)
        reason = "; ".join(reasons)
        return ScoringComponent(
            name="Sector",
            weight=0.0,
            score=score,
            weighted_score=0.0,
            reason=reason,
            data_source="Market Service",
        )

    def score_sentiment(self, stock_code: str, risk_level: RiskLevel = "moderate") -> ScoringComponent:
        score = 50.0
        reasons = []

        if risk_level == "low":
            score += 15
            reasons.append("Low risk profile")
        elif risk_level == "moderate":
            score += 10
            reasons.append("Moderate risk profile")
        elif risk_level == "high":
            score += 5
            reasons.append("High risk profile")

        accum = get_accumulation_status(stock_code)
        if accum is not None:
            status = accum.get("status", "")
            if status == "distributing":
                score -= 10
                reasons.append("Distribution detected")

        score = self._clamp(score)
        reason = "; ".join(reasons) if reasons else "Neutral sentiment"
        return ScoringComponent(
            name="Sentiment",
            weight=0.0,
            score=score,
            weighted_score=0.0,
            reason=reason,
            data_source="Market Service",
        )

    def calculate_score(
        self,
        stock_code: str,
        strategy: StrategyType = "swing",
        risk_level: RiskLevel = "moderate",
        df: Optional[pd.DataFrame] = None,
    ) -> ScoringResult:
        if df is None:
            data = fetch_stock_data(stock_code, period="6mo")
            if data is None:
                raise ValueError(f"Cannot fetch stock data for {stock_code}")
            df = calculate_indicators(data["history"])
            if df is None or df.empty:
                raise ValueError(f"Cannot calculate indicators for {stock_code}")

        if strategy == "swing":
            tech_weight = 0.10
            accum_weight = 0.25
            rs_weight = 0.15
        elif strategy == "day_trade":
            tech_weight = 0.20
            accum_weight = 0.15
            rs_weight = 0.10
        elif strategy == "long_term":
            tech_weight = 0.10
            accum_weight = 0.50
            rs_weight = 0.00
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        foreign_weight = 0.35
        sector_weight = 0.10
        sentiment_weight = 0.05

        tech = self.score_technical(df)
        foreign = self.score_foreign_flow(stock_code)
        accum = self.score_accumulation(stock_code)
        rs = self.score_relative_strength(stock_code)
        sector = self.score_sector(stock_code)
        sentiment = self.score_sentiment(stock_code, risk_level)

        weights = {
            "Technical": tech_weight,
            "Foreign Flow": foreign_weight,
            "Accumulation": accum_weight,
            "Relative Strength": rs_weight,
            "Sector": sector_weight,
            "Sentiment": sentiment_weight,
        }

        components = [tech, foreign, accum, rs, sector, sentiment]
        for c in components:
            w = weights.get(c.name, 0.0)
            c.weight = w
            c.weighted_score = round(c.score * w, 2)

        total_score = round(sum(c.weighted_score for c in components), 2)

        if total_score >= 80:
            recommendation = "STRONG_BUY"
        elif total_score >= 65:
            recommendation = "BUY"
        elif total_score >= 45:
            recommendation = "HOLD"
        elif total_score >= 30:
            recommendation = "SELL"
        else:
            recommendation = "STRONG_SELL"

        confidence = min(99, max(1, total_score))

        summary_parts = []
        for c in sorted(components, key=lambda x: x.weighted_score, reverse=True):
            if c.score >= 50:
                summary_parts.append(f"{c.name}: {c.reason}")
        summary = "; ".join(summary_parts[:3]) if summary_parts else "No strong signals"

        risks = [f"{c.name}: {c.reason}" for c in components if c.score < 40]
        catalysts = [f"{c.name}: {c.reason}" for c in components if c.score > 60]

        return ScoringResult(
            stock_code=stock_code.upper().replace(".JK", ""),
            strategy=strategy,
            risk_level=risk_level,
            components=components,
            total_score=total_score,
            recommendation=recommendation,
            confidence=confidence,
            summary=summary,
            risks=risks,
            catalysts=catalysts,
            last_updated=datetime.now().isoformat(),
        )
