import json
import os
from app.config import Config
from app.ai.providers import get_provider, get_all_providers, get_best_provider
from app.ai.knowledge_base import get_knowledge_for_prompt
from app.database import ai_crud


class AIAnalyzer:
    def __init__(self):
        self.providers = []

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
                    return self._normalize_result(result, data, provider.name)
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
            f"({data.get('change_pct'):+.2f}%), RSI {data.get('rsi')} ({data.get('rsi_status')}), "
            f"MACD {data.get('macd_status')}, Trend {data.get('trend')}, "
            f"MA20 Rp{data.get('ma20'):,.0f}, MA50 Rp{data.get('ma50'):,.0f}, "
            f"Support Rp{data.get('support'):,.0f}, Resistance Rp{data.get('resistance'):,.0f}, "
            f"Volume {data.get('volume_ratio')}x, Strategy {strategy}, Risk {risk_level}. "
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
        return "Anda adalah analis saham profesional untuk pasar Indonesia (IDX). Analisis data saham dan berikan rekomendasi BUY, HOLD, atau SELL. Output dalam format JSON."

    def _normalize_result(self, result, data, provider_name=""):
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
            "reasoning": f"[{provider_name}] " + result.get("reasoning", "") if provider_name else result.get("reasoning", ""),
            "full_analysis": result.get("full_analysis", ""),
            "ai_provider": provider_name,
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
            "ai_provider": "",
        }
