from typing import Optional
import pandas as pd
import numpy as np
from datetime import datetime


class CreativeTraderStrategy:
    """Creative Trader Long Term Strategy — accumulation-based entry detection.

    Analyzes foreign flow, price action, volume, and multi-timeframe alignment
    to identify institutional accumulation and generate entry signals.
    """

    def analyze_accumulation_phase(self, stock_code: str, lookback_days: int = 60) -> Optional[dict]:
        """Analyze accumulation phase from foreign flow and price data.

        Args:
            stock_code: Stock code (e.g. "BBCA")
            lookback_days: Lookback period for price data

        Returns:
            Dict with accumulation analysis, or None on failure
        """
        try:
            from app.database.foreign_flow_models import get_foreign_flow
            from app.services.stock_service import fetch_stock_data

            flow_data = get_foreign_flow(stock_code, days=20)
            if not flow_data:
                print(f"  ⚠ No foreign flow data for {stock_code}")
                return None

            accumulation_days = 0
            for r in flow_data:
                if r.get("foreign_net", 0) > 0:
                    accumulation_days += 1
                else:
                    break

            distribution_days = 0
            for r in flow_data:
                if r.get("foreign_net", 0) < 0:
                    distribution_days += 1
                else:
                    break

            cumulative_net_20d = sum(r.get("foreign_net", 0) for r in flow_data)
            positive_days = sum(1 for r in flow_data if r.get("foreign_net", 0) > 0)
            net_buy_ratio = (positive_days / len(flow_data)) * 100

            if accumulation_days >= 5:
                phase = "active_accumulation"
            elif accumulation_days >= 3 or net_buy_ratio >= 60:
                phase = "early_accumulation"
            elif distribution_days >= 5:
                phase = "heavy_distribution"
            elif distribution_days >= 3:
                phase = "early_distribution"
            else:
                phase = "neutral"

            stock_data = fetch_stock_data(stock_code, period="6mo")
            if stock_data is None:
                print(f"  ⚠ No stock data for {stock_code}")
                return None

            df = stock_data["history"]
            if df is None or df.empty or len(df) < 20:
                return None

            last_20 = df.tail(20)
            highest_high = last_20["High"].max()
            lowest_low = last_20["Low"].min()
            price_range_20d = ((highest_high - lowest_low) / lowest_low) * 100 if lowest_low > 0 else 0

            volume_avg_20d = float(last_20["Volume"].mean())
            volume_avg_5d = float(df.tail(5)["Volume"].mean())
            volume_trend = "increasing" if volume_avg_5d > volume_avg_20d else "decreasing"

            close_prices = last_20["Close"].values
            x = np.arange(len(close_prices))
            if len(close_prices) >= 2:
                coeffs = np.polyfit(x, close_prices, 1)
                price_slope = float(coeffs[0])
            else:
                price_slope = 0.0

            supply_absorbed = bool(
                price_range_20d < 5
                and volume_trend == "increasing"
                and abs(price_slope) < 1
            )

            closes = last_20["Close"].values
            avg_price = np.mean(closes)
            std_price = np.std(closes)
            upper_zone = float(avg_price + std_price)
            lower_zone = float(avg_price - std_price)
            current_price = float(df["Close"].iloc[-1])

            mid_threshold = std_price / 2
            if current_price > avg_price + mid_threshold:
                current_position = "near_upper"
            elif current_price < avg_price - mid_threshold:
                current_position = "near_lower"
            else:
                current_position = "mid"

            accum_points = min(accumulation_days * 4, 40)
            ratio_points = net_buy_ratio * 0.2
            supply_points = 20 if supply_absorbed else 0
            volume_points = 20 if volume_trend == "increasing" else 5
            confidence = min(100, max(0, accum_points + ratio_points + supply_points + volume_points))

            return {
                "stock_code": stock_code.upper().replace(".JK", ""),
                "phase": phase,
                "accumulation_days": accumulation_days,
                "distribution_days": distribution_days,
                "cumulative_net_20d": float(round(cumulative_net_20d, 2)),
                "net_buy_ratio": float(round(net_buy_ratio, 2)),
                "supply_absorbed": supply_absorbed,
                "hidden_accumulation": False,
                "price_range_20d": float(round(price_range_20d, 2)),
                "volume_trend": volume_trend,
                "avg_entry_zone": {
                    "upper": float(round(upper_zone, 2)),
                    "lower": float(round(lower_zone, 2)),
                    "current_position": current_position,
                },
                "current_price": current_price,
                "confidence": float(round(confidence, 2)),
            }
        except Exception as e:
            print(f"  ❌ analyze_accumulation_phase error for {stock_code}: {e}")
            return None

    def calculate_entry_point(self, stock_code: str) -> dict:
        """Calculate entry point based on accumulation analysis.

        Args:
            stock_code: Stock code (e.g. "BBCA")

        Returns:
            Dict with entry action, price range, stop loss, targets
        """
        try:
            accum = self.analyze_accumulation_phase(stock_code)
            if accum is None:
                return {
                    "action": "WAIT",
                    "entry_type": None,
                    "entry_price": 0,
                    "suggested_range": {"ideal": 0, "max": 0, "min": 0},
                    "stop_loss": 0,
                    "target_profit": {"short_term": 0, "medium_term": 0},
                    "risk_pct": 0,
                    "confidence": 0,
                    "reason": "Gagal mendapatkan data akumulasi",
                }

            from app.services.relative_strength import calculate_relative_strength

            phase = accum["phase"]
            supply_absorbed = accum["supply_absorbed"]
            position = accum["avg_entry_zone"]["current_position"]
            lower_zone = accum["avg_entry_zone"]["lower"]
            entry_price = float(accum["current_price"])

            rs_data = calculate_relative_strength(stock_code)
            rs_value = rs_data.get("rs_value", 0) if rs_data else 0

            if phase not in ("active_accumulation", "early_accumulation"):
                return {
                    "action": "WAIT",
                    "entry_type": None,
                    "entry_price": entry_price,
                    "suggested_range": {"ideal": 0, "max": 0, "min": 0},
                    "stop_loss": 0,
                    "target_profit": {"short_term": 0, "medium_term": 0},
                    "risk_pct": 0,
                    "confidence": accum["confidence"],
                    "reason": "Saham tidak dalam fase akumulasi",
                }

            if not supply_absorbed:
                return {
                    "action": "WAIT",
                    "entry_type": None,
                    "entry_price": entry_price,
                    "suggested_range": {"ideal": 0, "max": 0, "min": 0},
                    "stop_loss": 0,
                    "target_profit": {"short_term": 0, "medium_term": 0},
                    "risk_pct": 0,
                    "confidence": accum["confidence"],
                    "reason": "Harga belum sideways atau volume belum naik",
                }

            if rs_value <= 0:
                return {
                    "action": "WAIT",
                    "entry_type": None,
                    "entry_price": entry_price,
                    "suggested_range": {"ideal": 0, "max": 0, "min": 0},
                    "stop_loss": 0,
                    "target_profit": {"short_term": 0, "medium_term": 0},
                    "risk_pct": 0,
                    "confidence": accum["confidence"],
                    "reason": "Relative strength negatif terhadap IHSG",
                }

            if position == "near_upper":
                return {
                    "action": "WAIT",
                    "entry_type": None,
                    "entry_price": entry_price,
                    "suggested_range": {"ideal": 0, "max": 0, "min": 0},
                    "stop_loss": 0,
                    "target_profit": {"short_term": 0, "medium_term": 0},
                    "risk_pct": 0,
                    "confidence": accum["confidence"],
                    "reason": "Harga di upper zone akumulasi, tunggu pullback",
                }

            if position == "near_lower":
                action = "BUY"
                entry_type = "lumpsum"
            else:
                action = "ACCUMULATE"
                entry_type = "dca"

            stop_loss = round(lower_zone * 0.97, 2)
            short_term_target = round(entry_price * 1.06, 2)
            medium_term_target = round(entry_price * 1.15, 2)

            price_range = entry_price - lower_zone
            risk_pct = round((price_range / entry_price) * 100, 2) if entry_price > 0 else 0

            reason_map = {
                "BUY": "Entry di lower zone akumulasi dengan supply terserap",
                "ACCUMULATE": "DCA di area akumulasi, harga di mid zone",
            }

            return {
                "action": action,
                "entry_type": entry_type,
                "entry_price": entry_price,
                "suggested_range": {
                    "ideal": round(lower_zone, 2),
                    "max": round(lower_zone * 1.05, 2),
                    "min": round(lower_zone * 0.95, 2),
                },
                "stop_loss": stop_loss,
                "target_profit": {
                    "short_term": short_term_target,
                    "medium_term": medium_term_target,
                },
                "risk_pct": risk_pct,
                "confidence": accum["confidence"],
                "reason": reason_map.get(action, ""),
            }
        except Exception as e:
            print(f"  ❌ calculate_entry_point error for {stock_code}: {e}")
            return {
                "action": "WAIT",
                "entry_type": None,
                "entry_price": 0,
                "suggested_range": {"ideal": 0, "max": 0, "min": 0},
                "stop_loss": 0,
                "target_profit": {"short_term": 0, "medium_term": 0},
                "risk_pct": 0,
                "confidence": 0,
                "reason": f"Error: {e}",
            }

    def multi_timeframe_analysis(self, stock_code: str) -> dict:
        """Analyze stock across weekly, daily, and intraday timeframes.

        Args:
            stock_code: Stock code (e.g. "BBCA")

        Returns:
            Dict with timeframe outlooks and alignment status
        """
        try:
            from app.services.stock_service import fetch_stock_data, calculate_indicators

            weekly_outlook = "N/A"
            daily_phase = "N/A"
            intraday_momentum = "N/A"

            weekly_data = fetch_stock_data(stock_code, period="1y")
            if weekly_data is not None and weekly_data["history"] is not None and not weekly_data["history"].empty:
                wdf = weekly_data["history"]
                if len(wdf) >= 50:
                    weekly_resampled = wdf.resample("W-FRI").agg({
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum",
                    }).dropna()
                    if len(weekly_resampled) >= 50:
                        weekly_resampled["MA50"] = weekly_resampled["Close"].rolling(window=50).mean()
                        last_weekly_close = weekly_resampled["Close"].iloc[-1]
                        last_weekly_ma50 = weekly_resampled["MA50"].iloc[-1]
                        weekly_outlook = "Bullish" if pd.notna(last_weekly_ma50) and last_weekly_close > last_weekly_ma50 else "Bearish"
                    elif len(weekly_resampled) > 0:
                        weekly_outlook = "Bullish" if weekly_resampled["Close"].iloc[-1] > weekly_resampled["Close"].iloc[-2] else "Bearish"

            daily_data = fetch_stock_data(stock_code, period="6mo")
            if daily_data is not None and daily_data["history"] is not None:
                ddf = daily_data["history"]
                ddf_ind = calculate_indicators(ddf)
                if ddf_ind is not None and not ddf_ind.empty:
                    last = ddf_ind.iloc[-1]
                    prev = ddf_ind.iloc[-2] if len(ddf_ind) > 1 else last

                    ma20 = last.get("MA20")
                    ma50 = last.get("MA50")
                    close = last.get("Close")
                    trend = "Bullish"
                    if pd.notna(close) and pd.notna(ma20) and pd.notna(ma50):
                        if close > ma20 and ma20 > ma50:
                            trend = "Bullish"
                        elif close < ma20 and ma20 < ma50:
                            trend = "Bearish"
                        else:
                            trend = "Sideways"

                    rsi = last.get("RSI")
                    rsi_status = "Normal"
                    if pd.notna(rsi):
                        if rsi > 70:
                            rsi_status = "Overbought"
                        elif rsi < 30:
                            rsi_status = "Oversold"

                    macd_val = last.get("MACD")
                    macd_signal = last.get("MACD_Signal")
                    macd_status = "Bearish"
                    if pd.notna(macd_val) and pd.notna(macd_signal):
                        if macd_val > macd_signal and pd.notna(prev.get("MACD")) and pd.notna(prev.get("MACD_Signal")) and prev["MACD"] <= prev["MACD_Signal"]:
                            macd_status = "Golden Cross"
                        elif macd_val < macd_signal and pd.notna(prev.get("MACD")) and pd.notna(prev.get("MACD_Signal")) and prev["MACD"] >= prev["MACD_Signal"]:
                            macd_status = "Death Cross"
                        elif macd_val > macd_signal:
                            macd_status = "Bullish"
                        else:
                            macd_status = "Bearish"

                    accum = self.analyze_accumulation_phase(stock_code)
                    if accum is not None:
                        phase_map = {
                            "active_accumulation": "Akumulasi Aktif",
                            "early_accumulation": "Akumulasi Dini",
                            "heavy_distribution": "Distribusi Berat",
                            "early_distribution": "Distribusi Dini",
                            "neutral": "Netral",
                        }
                        daily_phase = phase_map.get(accum["phase"], "Netral")
                    else:
                        daily_phase = trend

            intraday_data = fetch_stock_data(stock_code, period="5d", interval="60m")
            if intraday_data is not None and intraday_data["history"] is not None and not intraday_data["history"].empty:
                idf = intraday_data["history"]
                if len(idf) >= 3:
                    last_3 = idf.tail(3)
                    bullish_candles = sum(1 for _, r in last_3.iterrows() if r["Close"] > r["Open"])
                    momentum_positif = bullish_candles >= 2

                    if len(idf) >= 2:
                        two_days_ago_close = idf["Close"].iloc[-2]
                        today_close = idf["Close"].iloc[-1]
                        pct_change = ((today_close - two_days_ago_close) / two_days_ago_close) * 100
                        pullback = pct_change <= -2

                        if pullback:
                            intraday_momentum = "Pullback opportunity"
                        elif momentum_positif:
                            intraday_momentum = "Momentum positif"
                        else:
                            intraday_momentum = "Sideways"
                    elif momentum_positif:
                        intraday_momentum = "Momentum positif"
                    else:
                        intraday_momentum = "Sideways"

            is_pullback = intraday_momentum == "Pullback opportunity"
            is_accumulating = daily_phase in ("Akumulasi Aktif", "Akumulasi Dini")
            is_bullish = weekly_outlook == "Bullish"

            if is_bullish and is_accumulating and is_pullback:
                alignment = "ALIGNED"
            elif not is_bullish and is_accumulating:
                alignment = "WARNING"
            elif is_bullish and not is_accumulating and is_pullback:
                alignment = "WARNING"
            else:
                alignment = "CONFLICT"

            return {
                "weekly_outlook": weekly_outlook,
                "daily_phase": daily_phase,
                "intraday_momentum": intraday_momentum,
                "alignment": alignment,
            }
        except Exception as e:
            print(f"  ❌ multi_timeframe_analysis error for {stock_code}: {e}")
            return {
                "weekly_outlook": "N/A",
                "daily_phase": "N/A",
                "intraday_momentum": "N/A",
                "alignment": "CONFLICT",
            }

    def scan_for_long_term_candidates(self, stock_codes: Optional[list[str]] = None) -> list[dict]:
        """Scan all stocks for long term accumulation candidates.

        Args:
            stock_codes: List of stock codes to scan, or None for all

        Returns:
            List of candidate dicts sorted by confidence descending
        """
        candidates = []
        try:
            from app.services.stock_service import STOCK_LIST
            from app.database.foreign_flow_models import get_accumulation_status
            from app.services.relative_strength import calculate_relative_strength

            codes = stock_codes if stock_codes is not None else list(STOCK_LIST.keys())

            for code in codes:
                try:
                    accum_status = get_accumulation_status(code)
                    if accum_status is None:
                        continue

                    if accum_status.get("accumulation_days", 0) < 3:
                        continue

                    accum = self.analyze_accumulation_phase(code)
                    if accum is None:
                        continue

                    rs_data = calculate_relative_strength(code)
                    rs_value = rs_data.get("rs_value", 0) if rs_data else 0

                    if accum["supply_absorbed"] and rs_value > 0:
                        candidates.append({
                            "stock_code": code.upper().replace(".JK", ""),
                            "phase": accum["phase"],
                            "accumulation_days": accum["accumulation_days"],
                            "confidence": accum["confidence"],
                            "current_price": accum["current_price"],
                        })
                except Exception as e:
                    print(f"  ⚠ Error scanning {code}: {e}")
                    continue
        except Exception as e:
            print(f"  ❌ scan_for_long_term_candidates error: {e}")

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates

    def analyze(self, stock_code: str) -> dict:
        """Run full long-term analysis for a stock.

        Args:
            stock_code: Stock code (e.g. "BBCA")

        Returns:
            Combined dict with accumulation, entry, timeframes, scoring
        """
        from app.services.stock_service import STOCK_LIST
        from app.ai.scoring_engine import ScoringEngine

        code = stock_code.upper().replace(".JK", "")
        stock_name = STOCK_LIST.get(code, "")

        accumulation = self.analyze_accumulation_phase(stock_code) or {}
        entry = self.calculate_entry_point(stock_code)
        timeframes = self.multi_timeframe_analysis(stock_code)

        scoring = {}
        try:
            scoring_result = ScoringEngine().calculate_score(stock_code, strategy="long_term")
            scoring = {
                "total_score": scoring_result.total_score,
                "recommendation": scoring_result.recommendation,
                "confidence": scoring_result.confidence,
                "summary": scoring_result.summary,
                "risks": scoring_result.risks,
                "catalysts": scoring_result.catalysts,
            }
        except Exception as e:
            print(f"  ⚠ Scoring error for {stock_code}: {e}")
            scoring = {"total_score": 0, "recommendation": "N/A", "confidence": 0}

        return {
            "stock_code": code,
            "stock_name": stock_name,
            "accumulation": accumulation,
            "entry": entry,
            "timeframes": timeframes,
            "scoring": scoring,
        }
