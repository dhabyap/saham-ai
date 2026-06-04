import json
import os
import numpy as np
from app.config import Config
from app.ai.providers import get_provider, get_all_providers, get_best_provider
from app.ai.knowledge_base import get_knowledge_for_prompt
from app.database import ai_crud

# In-memory cache: { "BBCA": {"date": "2026-06-04", "result": {...}} }
_analysis_cache = {}


class AIAnalyzer:
    def __init__(self):
        self.providers = []
        self.current_provider = None

    def _build_providers(self):
        configured = get_provider(Config.AI_PROVIDER)
        ordered = []

        if configured:
            ordered.append(configured)

        all_providers = get_all_providers()
        for p in all_providers:
            if not any(p.name == op.name for op in ordered):
                ordered.append(p)

        self.providers = ordered

    def is_available(self):
        self._build_providers()
        return any(p.has_config() for p in self.providers)

    def analyze(self, data, strategy="swing", risk_level="moderate"):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"{data.get('stock_code')}_{strategy}_{risk_level}"

        # 1) in-memory cache (same day)
        if cache_key in _analysis_cache and _analysis_cache[cache_key]["date"] == today:
            cached = dict(_analysis_cache[cache_key]["result"])
            cached["source"] = "cache"
            return cached

        # 2) DB cache (same day)
        db_cached = ai_crud.get_analysis_cache(cache_key, today)
        if db_cached:
            normalized = self._normalize_result(db_cached, data, db_cached.get("ai_provider", "9router"))
            normalized["source"] = "database"
            _analysis_cache[cache_key] = {"date": today, "result": normalized}
            return normalized

        self._build_providers()
        knowledge = get_knowledge_for_prompt(data, strategy)
        prompt = self._build_prompt(data, strategy, risk_level, knowledge)
        custom_prompt = ai_crud.get_prompt("custom_analyst")
        system_prompt = custom_prompt["prompt_text"] if custom_prompt else self._get_default_system_prompt()

        tried = []
        for provider in self.providers:
            if not provider.is_available():
                continue
            tried.append(provider.name)
            try:
                result = provider.analyze(prompt, system_prompt)
                if result:
                    normalized = self._normalize_result(result, data, provider.name)
                    # Save to both caches
                    normalized["source"] = "ai_api"
                    _analysis_cache[cache_key] = {"date": today, "result": normalized}
                    ai_crud.save_analysis_cache(cache_key, strategy, risk_level, normalized)
                    return normalized
            except Exception as e:
                safe = str(e).encode("ascii", "ignore").decode("ascii")
                print(f"  {provider.name}: {safe[:120]}")

        if tried:
            print(f"  All AI providers failed: {', '.join(tried)}")
        return self._fallback_analysis(data)

    def analyze_sentiment(self, market_data):
        self._build_providers()
        prompt = self._build_sentiment_prompt(market_data)
        custom_prompt = ai_crud.get_prompt("custom_analyst")
        system_prompt = custom_prompt["prompt_text"] if custom_prompt else self._get_default_system_prompt()

        for provider in self.providers:
            if not provider.is_available():
                continue
            try:
                result = provider.analyze(prompt, system_prompt)
                if result:
                    return result
            except Exception:
                pass
        return None

    def _build_prompt(self, data, strategy, risk_level, knowledge=""):
        return (
            f"Analisa {data.get('stock_code')}: Harga Rp{data.get('price'):,.0f} "
            f"({data.get('change_pct', 0):+.2f}%), RSI {data.get('rsi')} ({data.get('rsi_status')}), "
            f"MACD {data.get('macd_status')}, Trend {data.get('trend')}, "
            f"MA20 Rp{data.get('ma20', 0):,.0f}, MA50 Rp{data.get('ma50', 0):,.0f}, "
            f"Support Rp{data.get('support', 0):,.0f}, Resistance Rp{data.get('resistance', 0):,.0f}, "
            f"Volume {data.get('volume_ratio', 1)}x, Strategy {strategy}, Risk {risk_level}. "
            f"{knowledge}"
            f"Output JSON: trend, recommendation(BUY/HOLD/SELL), confidence(0-100), reasoning."
        )

    def _build_sentiment_prompt(self, market_data):
        return f"""Analisis sentimen market:

Advancing: {market_data.get('advancing')}
Declining: {market_data.get('declining')}
Fear & Greed: {market_data.get('fear_greed', {}).get('index')} - {market_data.get('fear_greed', {}).get('label')}
Avg Change: {market_data.get('avg_change')}%

Output JSON:
{{
  "sentiment": "Bullish/Neutral/Bearish",
  "sentiment_score": 0-100,
  "analysis": "..."
}}"""

    def _get_default_system_prompt(self):
        return (
            "Anda adalah analis saham profesional untuk pasar Indonesia (IDX). "
            "Analisis data saham dan berikan rekomendasi BUY, HOLD, atau SELL. "
            "PENTING: Output HARUS dalam format JSON saja, tanpa penjelasan tambahan atau teks lainnya. "
            "Confidence HARUS berupa angka 0-100, bukan string. "
            "Contoh: {\"trend\": \"Bullish\", \"recommendation\": \"BUY\", \"confidence\": 80, \"reasoning\": \"RSI oversold, volume spike, support kuat.\"}"
        )

    def _normalize_result(self, result, data, provider_name=""):
        def _to_python(val):
            """Convert numpy/pandas types to native Python for JSON serialization."""
            if val is None:
                return None
            if isinstance(val, (np.integer,)):
                return int(val)
            if isinstance(val, (np.floating,)):
                return float(val)
            if isinstance(val, (np.bool_,)):
                return bool(val)
            return val

        # Normalize confidence to int
        raw_conf = result.get("confidence", 50)
        if isinstance(raw_conf, str):
            conf_map = {"high": 85, "medium": 60, "low": 35, "very high": 90, "very low": 20}
            confidence = conf_map.get(raw_conf.lower(), 50)
        else:
            try:
                confidence = int(float(raw_conf))
            except (ValueError, TypeError):
                confidence = 50
        confidence = max(1, min(99, confidence))

        # Normalize recommendation
        rec = result.get("recommendation", "HOLD").upper()
        if rec not in ("BUY", "HOLD", "SELL"):
            rec = "HOLD"

        return {
            "trend": str(result.get("trend", data.get("trend", "Sideways"))),
            "rsi_analysis": str(result.get("rsi_analysis", "")),
            "macd_analysis": str(result.get("macd_analysis", "")),
            "momentum": str(result.get("momentum", "Neutral")),
            "risk": str(result.get("risk", "Medium")),
            "support_level": _to_python(result.get("support_level", data.get("support"))),
            "resistance_level": _to_python(result.get("resistance_level", data.get("resistance"))),
            "recommendation": rec,
            "confidence": confidence,
            "reasoning": f"[{provider_name}] " + str(result.get("reasoning", "")) if provider_name else str(result.get("reasoning", "")),
            "full_analysis": str(result.get("full_analysis", "")),
            "ai_provider": provider_name,
        }

    def _fallback_analysis(self, data):
        def _to_python(val):
            if val is None:
                return None
            if isinstance(val, (np.integer,)):
                return int(val)
            if isinstance(val, (np.floating,)):
                return float(val)
            if isinstance(val, (np.bool_,)):
                return bool(val)
            return val

        return {
            "trend": str(data.get("trend", "Sideways")),
            "rsi_analysis": f"RSI: {data.get('rsi')} ({data.get('rsi_status')})" if data.get('rsi') else "N/A",
            "macd_analysis": f"MACD: {data.get('macd_status')}" if data.get('macd_status') else "N/A",
            "momentum": "Neutral",
            "risk": "Medium",
            "support_level": _to_python(data.get("support")),
            "resistance_level": _to_python(data.get("resistance")),
            "recommendation": "HOLD",
            "confidence": 50,
            "reasoning": "AI analysis tidak tersedia. Menggunakan analisis rule-based.",
            "full_analysis": "AI analysis tidak tersedia karena API key belum dikonfigurasi.",
            "ai_provider": "",
            "source": "rule_based",
        }

    def analyze_for_day_trading(self, stock_code, features, context=None):
        """
        Analyze stock for day trading (buy morning, sell evening)
        
        Args:
            stock_code: Stock code (e.g., BBCA)
            features: Dict with open, high, low, close, volume, sma_20, rsi, macd
            context: Additional context
            
        Returns:
            Dict with signal, confidence, expected_profit, risk_level, reasoning
        """
        self._build_providers()
        
        # Build day trading specific prompt
        prompt = self._build_day_trading_prompt(stock_code, features)
        system_prompt = "Anda adalah trader profesional IDX. Analisis untuk day trading (beli pagi, jual sore). Berikan rekomendasi BUY, SELL, atau HOLD. Output dalam format JSON dengan fields: signal, confidence (0-1), expected_profit, risk_level (LOW/MEDIUM/HIGH), reasoning."
        
        for provider in self.providers:
            if not provider.is_available():
                continue
            try:
                result = provider.analyze(prompt, system_prompt)
                if result:
                    self.current_provider = provider.name
                    return self._parse_day_trading_result(result, stock_code)
            except Exception as e:
                print(f"  {provider.name} day trading error: {str(e)[:100]}")
        
        # Fallback to rule-based analysis
        self.current_provider = "rule_based"
        return self._day_trading_fallback(stock_code, features)
    
    def _build_day_trading_prompt(self, stock_code, features):
        """Build prompt for day trading analysis"""
        return f"""Analisis untuk day trading saham {stock_code}:

Data:
- Open: Rp{features.get('open', 0):,.0f}
- High: Rp{features.get('high', 0):,.0f}
- Low: Rp{features.get('low', 0):,.0f}
- Close: Rp{features.get('close', 0):,.0f}
- Volume: {features.get('volume', 0):,}
- SMA 20: Rp{features.get('sma_20', 0):,.0f}
- RSI: {features.get('rsi', 50):.1f}
- MACD: {features.get('macd', 0):.4f}

Pertimbangan:
1. Apakah harga berada di atas/bawah SMA 20?
2. Apakah RSI menunjukkan oversold (<30) atau overbought (>70)?
3. Apakah MACD positif dan trending up?
4. Apakah volume cukup untuk day trading?

Output JSON:
{{
  "signal": "BUY/SELL/HOLD",
  "confidence": 0.0-1.0,
  "expected_profit": 0.0-5.0,
  "risk_level": "LOW/MEDIUM/HIGH",
  "reasoning": "..."
}}"""
    
    def _parse_day_trading_result(self, result, stock_code):
        """Parse AI result for day trading"""
        try:
            # Extract JSON if needed
            if isinstance(result, str):
                import json
                result = json.loads(result)
            
            signal = result.get("signal", "HOLD").upper()
            confidence = float(result.get("confidence", 0.5))
            expected_profit = float(result.get("expected_profit", 0))
            risk_level = result.get("risk_level", "MEDIUM").upper()
            reasoning = result.get("reasoning", "")
            
            # Validate values
            confidence = max(0, min(1, confidence))
            expected_profit = max(-5, min(5, expected_profit))
            
            if signal not in ["BUY", "SELL", "HOLD"]:
                signal = "HOLD"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "expected_profit": expected_profit,
                "risk_level": risk_level,
                "reasoning": reasoning
            }
        except Exception as e:
            print(f"Error parsing day trading result: {e}")
            return self._day_trading_fallback_result(stock_code, result)
    
    def _day_trading_fallback(self, stock_code, features):
        """Rule-based day trading analysis"""
        signal = "HOLD"
        confidence = 0.5
        expected_profit = 0
        risk_level = "MEDIUM"
        reasoning = ""
        
        rsi = features.get('rsi', 50)
        macd = features.get('macd', 0)
        close = features.get('close', 0)
        sma_20 = features.get('sma_20', 0)
        high = features.get('high', 0)
        low = features.get('low', 0)
        volume = features.get('volume', 0)
        
        # Simple rule-based logic
        buy_signals = 0
        sell_signals = 0
        
        # RSI analysis
        if rsi < 30:
            buy_signals += 1
            reasoning += "RSI oversold. "
        elif rsi > 70:
            sell_signals += 1
            reasoning += "RSI overbought. "
        
        # MACD analysis
        if macd > 0:
            buy_signals += 1
            reasoning += "MACD positif. "
        elif macd < 0:
            sell_signals += 1
            reasoning += "MACD negatif. "
        
        # Price vs SMA analysis
        if close > sma_20:
            buy_signals += 1
            reasoning += "Harga di atas SMA20. "
        else:
            sell_signals += 1
            reasoning += "Harga di bawah SMA20. "
        
        # Determine signal
        if buy_signals > sell_signals:
            signal = "BUY"
            confidence = min(0.95, 0.5 + (buy_signals * 0.15))
            expected_profit = 1.5 if buy_signals >= 2 else 0.8
            risk_level = "LOW" if buy_signals >= 3 else "MEDIUM"
        elif sell_signals > buy_signals:
            signal = "SELL"
            confidence = min(0.95, 0.5 + (sell_signals * 0.15))
            expected_profit = 1.5 if sell_signals >= 2 else 0.8
            risk_level = "LOW" if sell_signals >= 3 else "MEDIUM"
        else:
            reasoning = "Sinyal tidak jelas, tunggu momentum lebih jelas."
            risk_level = "HIGH"
        
        if not reasoning:
            reasoning = "Analisis berdasarkan rule (AI provider tidak tersedia)"
        
        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "expected_profit": round(expected_profit, 2),
            "risk_level": risk_level,
            "reasoning": reasoning
        }
    
    def _day_trading_fallback_result(self, stock_code, raw_result):
        """Handle error in parsing - return safe fallback"""
        return {
            "signal": "HOLD",
            "confidence": 0.5,
            "expected_profit": 0,
            "risk_level": "HIGH",
            "reasoning": f"Error parsing AI response for {stock_code}"
        }
