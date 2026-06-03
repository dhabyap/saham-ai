import json
import os
from app.config import Config
from app.ai.providers import get_provider, get_best_provider
from app.ai.knowledge_base import get_knowledge_for_prompt
from app.database import ai_crud


class AIAnalyzer:
    def __init__(self):
        self.provider = None
        self._init_provider()

    def _init_provider(self):
        config_provider = get_provider(Config.AI_PROVIDER)
        if config_provider and config_provider.is_available():
            self.provider = config_provider
            return
        best = get_best_provider()
        if best:
            self.provider = best

    def is_available(self):
        if self.provider and self.provider.is_available():
            return True
        self._init_provider()
        return self.provider is not None and self.provider.is_available()

    def analyze(self, data, strategy="swing", risk_level="moderate"):
        if self.is_available():
            try:
                knowledge = get_knowledge_for_prompt(data, strategy)
                prompt = self._build_prompt(data, strategy, risk_level, knowledge)
                custom_prompt = ai_crud.get_prompt("custom_analyst")
                system_prompt = custom_prompt["prompt_text"] if custom_prompt else self._get_default_system_prompt()
                result = self.provider.analyze(prompt, system_prompt)
                if result:
                    return self._normalize_result(result, data)
            except Exception as e:
                print(f"AI analyze error: {e}")
        return self._fallback_analysis(data)

    def analyze_sentiment(self, market_data):
        if self.is_available():
            try:
                prompt = self._build_sentiment_prompt(market_data)
                result = self.provider.analyze(prompt)
                if result:
                    return result
            except Exception:
                pass
        return None

    def _build_prompt(self, data, strategy, risk_level, knowledge=""):
        return f"""Analisis saham berikut:

Stock: {data.get('stock_code')} - {data.get('stock_name')}
Price: Rp{data.get('price'):,.0f}
Change: {data.get('change_pct')}%
RSI: {data.get('rsi')} ({data.get('rsi_status')})
MACD: {data.get('macd_status')}
MA20: Rp{data.get('ma20'):,.0f}
MA50: Rp{data.get('ma50'):,.0f}
Trend: {data.get('trend')}
Support: Rp{data.get('support'):,.0f}
Resistance: Rp{data.get('resistance'):,.0f}
Volume Ratio: {data.get('volume_ratio')}x
Volume Spike: {data.get('volume_spike')}
Strategy: {strategy}
Risk Level: {risk_level}

{knowledge}

Output JSON:
{{
  "trend": "Bullish/Bearish/Sideways",
  "rsi_analysis": "...",
  "macd_analysis": "...",
  "momentum": "Strong/Weak/Neutral",
  "risk": "Low/Medium/High",
  "support_level": {data.get('support')},
  "resistance_level": {data.get('resistance')},
  "recommendation": "BUY/HOLD/SELL",
  "confidence": 0-100,
  "reasoning": "Penjelasan singkat",
  "full_analysis": "Analisa lengkap dalam 2-3 paragraf"
}}"""

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
        return "Anda adalah analis saham profesional untuk pasar Indonesia (IDX). Analisis data saham dan berikan rekomendasi BUY, HOLD, atau SELL. Output dalam format JSON."

    def _normalize_result(self, result, data):
        return {
            "trend": result.get("trend", data.get("trend", "Sideways")),
            "rsi_analysis": result.get("rsi_analysis", ""),
            "macd_analysis": result.get("macd_analysis", ""),
            "momentum": result.get("momentum", "Neutral"),
            "risk": result.get("risk", "Medium"),
            "support_level": result.get("support_level", data.get("support")),
            "resistance_level": result.get("resistance_level", data.get("resistance")),
            "recommendation": result.get("recommendation", "HOLD"),
            "confidence": result.get("confidence", 50),
            "reasoning": result.get("reasoning", ""),
            "full_analysis": result.get("full_analysis", ""),
        }

    def _fallback_analysis(self, data):
        return {
            "trend": data.get("trend", "Sideways"),
            "rsi_analysis": f"RSI: {data.get('rsi')} ({data.get('rsi_status')})" if data.get('rsi') else "N/A",
            "macd_analysis": f"MACD: {data.get('macd_status')}" if data.get('macd_status') else "N/A",
            "momentum": "Neutral",
            "risk": "Medium",
            "support_level": data.get("support"),
            "resistance_level": data.get("resistance"),
            "recommendation": "HOLD",
            "confidence": 50,
            "reasoning": "AI analysis tidak tersedia. Menggunakan analisis rule-based.",
            "full_analysis": "AI analysis tidak tersedia karena API key belum dikonfigurasi.",
        }
