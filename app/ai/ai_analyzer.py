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
            normalized = self._normalize_result(db_cached, data, db_cached.get("ai_provider", ""))
            normalized["source"] = "database"
            _analysis_cache[cache_key] = {"date": today, "result": normalized}
            return normalized

        self._build_providers()
        knowledge = get_knowledge_for_prompt(data, strategy)
        prompt = self._build_prompt(data, strategy, risk_level, knowledge)
        custom_prompt = ai_crud.get_prompt("custom_analyst")
        system_prompt = custom_prompt["prompt_text"] if custom_prompt else self._get_default_system_prompt()

        tried = []
        last_error = ""
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
                last_error = f"{provider.name}: {safe[:200]}"
                print(f"  {last_error}")

        ai_error = f"AI gagal: {', '.join(tried)}" if tried else "Tidak ada provider AI"
        if last_error:
            ai_error += f" ({last_error})"
        print(f"  {ai_error}")
        result = self._fallback_analysis(data)
        result["ai_error"] = ai_error
        return result

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
        foreign_flow = data.get('foreign_net_buy', 'N/A')
        accumulation_days = data.get('accumulation_days', 0)
        relative_strength = data.get('relative_strength', 'N/A')
        sector = data.get('sector', 'N/A')
        sector_flow = data.get('sector_flow', 'N/A')

        if isinstance(foreign_flow, (int, float)):
            foreign_line = f"Foreign Net Buy: Rp{foreign_flow:,.0f}"
        else:
            foreign_line = f"Foreign Net Buy: {foreign_flow}"

        return (
            f"Analisa {data.get('stock_code')} menggunakan Money Flow Methodology:\n"
            f"Harga Rp{data.get('price'):,.0f} ({data.get('change_pct', 0):+.2f}%), "
            f"Volume {data.get('volume_ratio', 1)}x rata-rata\n"
            f"\n=== MONEY FLOW ===\n"
            f"{foreign_line}\n"
            f"Akumulasi/Distribusi: {accumulation_days} hari akumulasi\n"
            f"Relative Strength vs IHSG: {relative_strength}\n"
            f"Sektor: {sector} ({sector_flow})\n"
            f"\n=== TEKNIKAL ===\n"
            f"RSI {data.get('rsi')} ({data.get('rsi_status')}), "
            f"MACD {data.get('macd_status')}, Trend {data.get('trend')}, "
            f"MA20 Rp{data.get('ma20', 0):,.0f}, MA50 Rp{data.get('ma50', 0):,.0f}, "
            f"Support Rp{data.get('support', 0):,.0f}, Resistance Rp{data.get('resistance', 0):,.0f}\n"
            f"Strategy: {strategy}, Risk: {risk_level}\n"
            f"{knowledge}\n"
            f"Output JSON sesuai format analyst_prompt.txt"
        )

    def _build_sentiment_prompt(self, market_data):
        return f"""Analisis sentimen market berdasarkan institutional flow:

Advancing: {market_data.get('advancing')}
Declining: {market_data.get('declining')}
Fear & Greed: {market_data.get('fear_greed', {}).get('index')} - {market_data.get('fear_greed', {}).get('label')}
Avg Change: {market_data.get('avg_change')}%

Output JSON sesuai format sentiment_prompt.txt"""

    def _get_default_system_prompt(self):
        return (
            "Anda adalah analis saham profesional untuk pasar Indonesia (IDX) spesialis Money Flow Analysis. "
            "Prioritas analisis: Foreign Flow (35%), Accumulation/Distribution (25%), "
            "Relative Strength vs IHSG (15%), Sector Rotation (10%), Volume (10%), "
            "Technical sebagai konfirmasi (5%). "
            "'Harga mengikuti uang.' "
            "Output HARUS dalam format JSON saja, tanpa teks tambahan. "
            "Gunakan field: trend, money_flow_analysis, accumulation_status, accumulation_days, "
            "relative_strength, sector, sector_flow, volume_analysis, rsi_analysis, macd_analysis, "
            "momentum, risk, support_level, resistance_level, recommendation(BUY/HOLD/SELL), "
            "confidence(0-100), reasoning, full_analysis."
        )

    def _calculate_dynamic_confidence(self, data):
        """Confidence based on technical indicators, not AI guess."""
        score = 50

        trend = data.get('trend', 'Sideways')
        if trend in ('Bullish', 'Bearish'):
            score += 10
        elif trend in ('Bullish (short term)', 'Bearish (short term)'):
            score += 5

        rsi_status = data.get('rsi_status', 'Normal')
        rsi = data.get('rsi')
        if rsi_status == 'Overbought':
            score += 8 if (rsi and rsi > 75) else 4
        elif rsi_status == 'Oversold':
            score += 8 if (rsi and rsi < 25) else 4

        macd = data.get('macd_status', '')
        if 'Golden Cross' in macd or 'Death Cross' in macd:
            score += 15
        elif macd in ('Bullish', 'Bearish'):
            score += 7

        if data.get('volume_spike'):
            score += 10
        elif data.get('volume_ratio', 1) > 2:
            score += 7
        elif data.get('volume_ratio', 1) > 1.5:
            score += 4

        change = abs(data.get('change_pct', 0))
        if change > 5:
            score += 10
        elif change > 3:
            score += 6
        elif change > 1.5:
            score += 3

        if data.get('near_support') and 'Bullish' in trend:
            score += 8
        elif data.get('near_support'):
            score += 2
        if data.get('near_resistance') and 'Bearish' in trend:
            score += 8
        elif data.get('near_resistance'):
            score += 2

        return max(1, min(99, score))

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
        # Override with data-driven confidence 
        confidence = self._calculate_dynamic_confidence(data)

        # Normalize recommendation
        rec = result.get("recommendation", "HOLD").upper()
        if rec not in ("BUY", "HOLD", "SELL"):
            rec = "HOLD"

        return {
            "trend": str(result.get("trend", data.get("trend", "Sideways"))),
            "money_flow_analysis": str(result.get("money_flow_analysis", "")),
            "accumulation_status": str(result.get("accumulation_status", "NETRAL")),
            "accumulation_days": int(result.get("accumulation_days", data.get("accumulation_days", 0))),
            "relative_strength": str(result.get("relative_strength", "NEUTRAL")),
            "sector": str(result.get("sector", data.get("sector", ""))),
            "sector_flow": str(result.get("sector_flow", "NEUTRAL")),
            "volume_analysis": str(result.get("volume_analysis", "")),
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
            "money_flow_analysis": f"Foreign Net Buy: Rp{data.get('foreign_net_buy', 0):,.0f}" if data.get('foreign_net_buy') else "Data foreign flow tidak tersedia",
            "accumulation_status": "NETRAL",
            "accumulation_days": int(data.get("accumulation_days", 0)),
            "relative_strength": str(data.get("relative_strength", "NEUTRAL")),
            "sector": str(data.get("sector", "")),
            "sector_flow": str(data.get("sector_flow", "NEUTRAL")),
            "volume_analysis": f"Volume: {data.get('volume_ratio', 1)}x rata-rata" if data.get('volume_ratio') else "N/A",
            "rsi_analysis": f"RSI: {data.get('rsi')} ({data.get('rsi_status')})" if data.get('rsi') else "N/A",
            "macd_analysis": f"MACD: {data.get('macd_status')}" if data.get('macd_status') else "N/A",
            "momentum": "Neutral",
            "risk": "Medium",
            "support_level": _to_python(data.get("support")),
            "resistance_level": _to_python(data.get("resistance")),
            "recommendation": "HOLD",
            "confidence": self._calculate_dynamic_confidence(data),
            "reasoning": "AI analysis tidak tersedia. Menggunakan analisis rule-based.",
            "full_analysis": "AI analysis tidak tersedia karena API key belum dikonfigurasi.",
            "ai_provider": "",
            "source": "rule_based",
        }

    def analyze_for_day_trading(self, stock_code, features, context=None):
        """
        Analyze stock for day trading — Money Flow & Accumulation Centric Method
        
        Args:
            stock_code: Stock code (e.g., BBCA)
            features: Dict with open, high, low, close, volume, sma_20, rsi, macd,
                      foreign_net_buy, foreign_accumulation_days, broker_buy, broker_sell,
                      ihsg_change, sector
            context: Additional context
            
        Returns:
            Dict with signal, confidence, expected_profit, risk_level, reasoning
        """
        self._build_providers()
        
        # Build day trading specific prompt
        prompt = self._build_day_trading_prompt(stock_code, features)
        system_prompt = (
            "Anda adalah trader profesional IDX spesialis Money Flow Trading. "
            "Analisis day trading berdasarkan prioritas: "
            "(1) Opening Drive — apakah harga buka menunjukkan minat beli, "
            "(2) Volume Spike — volume > rata-rata + kenaikan harga = konfirmasi, "
            "(3) Foreign Buy Morning — foreign net buy di awal sesi, "
            "(4) Tick Index — jumlah tick naik vs turun. "
            "Entry jika 3 dari 4 faktor konfirmasi. Target 1-2%, Stop Loss 0.5-1%. "
            "Risk/Reward minimal 1:2. "
            "Output JSON: signal(BUY/SELL/HOLD), confidence(0-1), expected_profit(%), "
            "risk_level(LOW/MEDIUM/HIGH), reasoning, opening_drive, volume_confirmation, "
            "foreign_flow_note, tick_index_note"
        )
        
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
        """Build prompt for day trading — Money Flow methodology"""
        foreign_net = features.get('foreign_net_buy', 0)
        accum_days = features.get('foreign_accumulation_days', 0)
        broker_buy = features.get('broker_buy', 'N/A')
        broker_sell = features.get('broker_sell', 'N/A')
        ihsg = features.get('ihsg_change', 0)
        
        return f"""Analisis DAY TRADING saham {stock_code} — Money Flow Method:

=== DATA HARGA ===
- Open: Rp{features.get('open', 0):,.0f}
- High: Rp{features.get('high', 0):,.0f}
- Low: Rp{features.get('low', 0):,.0f}
- Close: Rp{features.get('close', 0):,.0f}
- Range: {features.get('range_pct', 0):.2f}%
- Volume: {features.get('volume', 0):,}

=== MONEY FLOW ===
- Foreign Net Buy: Rp{foreign_net:,.0f}
- Foreign Accumulation Days: {accum_days}
- Broker Buy (Rp): {broker_buy}
- Broker Sell (Rp): {broker_sell}
- IHSG Change: {ihsg:+.2f}%
- Sector: {features.get('sector', 'N/A')}

=== TEKNIKAL ===
- SMA 20: Rp{features.get('sma_20', 0):,.0f}
- RSI: {features.get('rsi', 50):.1f}
- MACD: {features.get('macd', 0):.4f}

=== ANALISIS DAY TRADING ===
1. OPENING DRIVE: Apakah harga open di atas low yesterday? Apakah ada gap up/down?
2. VOLUME SPIKE: Volume vs rata-rata. Volume > 1.5x = konfirmasi.
3. FOREIGN BUY: Apakah foreign net buy positif? Accumulation berapa hari?
4. TICK INDEX: Broker buy vs sell — siapa dominan?
5. TEKNIKAL: Entry jika 3 dari 4 faktor di atas konfirmasi, teknikal hanya konfirmasi.

Output JSON:
{{
  "signal": "BUY/SELL/HOLD",
  "confidence": 0.0-1.0,
  "expected_profit": 0.0-2.0,
  "risk_level": "LOW/MEDIUM/HIGH",
  "opening_drive": "gap_up/gap_down/netral + analisis",
  "volume_confirmation": "ya/tidak + volume ratio",
  "foreign_flow_note": "analisis foreign buy/s pagi ini",
  "tick_index_note": "broker dominan dan arahnya",
  "reasoning": "Kesimpulan berdasarkan money flow methodology"
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
                "reasoning": reasoning,
                "opening_drive": result.get("opening_drive", ""),
                "volume_confirmation": result.get("volume_confirmation", ""),
                "foreign_flow_note": result.get("foreign_flow_note", ""),
                "tick_index_note": result.get("tick_index_note", ""),
            }
        except Exception as e:
            print(f"Error parsing day trading result: {e}")
            return self._day_trading_fallback_result(stock_code, result)
    
    def _day_trading_fallback(self, stock_code, features):
        """
        Rule-based day trading — 7-Level Money Flow methodology
        Prioritas: Opening Drive, Volume Spike, Foreign Buy, Tick Index, Teknikal
        """
        signal = "HOLD"
        confidence = 0.5
        expected_profit = 0
        risk_level = "MEDIUM"
        reasoning = ""
        
        close = features.get('close', 0)
        open_price = features.get('open', 0)
        high = features.get('high', 0)
        low = features.get('low', 0)
        volume = features.get('volume', 0)
        rsi = features.get('rsi', 50)
        macd = features.get('macd', 0)
        sma_20 = features.get('sma_20', 0)
        
        # New money flow features
        foreign_net = features.get('foreign_net_buy', 0)
        accum_days = features.get('foreign_accumulation_days', 0)
        ihsg = features.get('ihsg_change', 0)
        
        # === 7-LEVEL SCORING ===
        score = 0
        max_score = 7
        details = []
        
        # 1) OPENING DRIVE: harga open vs close sebelumnya (proksi: open vs SMA20)
        if open_price > sma_20 and open_price > close * 0.99:
            score += 1
            details.append("Opening Drive: harga buka di atas SMA20, momentum positif")
        elif open_price < sma_20:
            details.append("Opening Drive: harga buka di bawah SMA20, hati-hati")
        
        # 2) VOLUME SPIKE: volume > rata-rata (proksi: ada volume masuk)
        if volume > 0 and close > 0:
            volume_value = volume * close  # Rupiah value proxy
            if volume_value > 0:
                score += 1
                details.append("Volume Spike: volume terkonfirmasi")
        
        # 3) FOREIGN BUY: foreign net buy positif
        if foreign_net > 0:
            score += 1
            details.append(f"Foreign Buy: net buy Rp{foreign_net:,.0f}")
        if accum_days >= 3:
            score += 1
            details.append(f"Akumulasi: {accum_days} hari berturut-turut")
        elif accum_days >= 1:
            details.append(f"Akumulasi: {accum_days} hari")
        
        # 4) RELATIVE STRENGTH: saham lebih kuat dari IHSG
        if ihsg > 0:
            score += 1
            details.append("Relative Strength: saham outperform IHSG")
        
        # 5) TEKNIKAL: RSI + MACD sebagai konfirmasi
        if 30 <= rsi <= 70:
            if rsi < 40:
                score += 1
                details.append("RSI oversold area, potensi reversal")
            elif rsi > 60:
                details.append("RSI overbought area, waspadai koreksi")
        elif rsi < 30:
            score += 1
            details.append("RSI oversold, potensi bounce")
        
        if macd > 0:
            score += 1
            details.append("MACD positif, momentum naik")
        
        # === DECISION BASED ON SCORE ===
        # Entry jika 3 dari 4 faktor utama konfirmasi (Opening Drive, Volume, Foreign, Relative)
        # Teknikal hanya konfirmasi
        
        if score >= 5:
            signal = "BUY"
            confidence = 0.5 + (score * 0.07)
            expected_profit = 1.5 if accum_days >= 3 else 1.0
            risk_level = "LOW"
            reasoning = "BUY: " + " | ".join(details[:4])
        elif score >= 3:
            signal = "BUY"
            confidence = 0.5 + (score * 0.05)
            expected_profit = 1.0
            risk_level = "MEDIUM"
            reasoning = "BUY (konservatif): " + " | ".join(details[:3])
        elif score <= 1 and foreign_net < 0:
            signal = "SELL"
            confidence = 0.6
            expected_profit = 0.5
            risk_level = "HIGH"
            reasoning = "SELL: Foreign net sell, skor rendah"
        else:
            reasoning = "HOLD: Sinyal tidak konklusif. Tunggu konfirmasi Opening Drive + Foreign Buy."
            risk_level = "HIGH"
        
        if not reasoning:
            reasoning = "Analisis Money Flow rule-based (AI provider tidak tersedia)"
        
        return {
            "signal": signal,
            "confidence": round(min(confidence, 0.95), 2),
            "expected_profit": round(expected_profit, 2),
            "risk_level": risk_level,
            "reasoning": reasoning,
            "opening_drive": "positif" if open_price > sma_20 else "negatif",
            "volume_confirmation": "ya" if volume > 0 else "tidak",
            "foreign_flow_note": f"Net Buy: Rp{foreign_net:,.0f}, Accum: {accum_days} hari" if foreign_net != 0 else "Data foreign tidak tersedia",
            "tick_index_note": f"Skor akhir: {score}/{max_score}",
        }
    
    def _day_trading_fallback_result(self, stock_code, raw_result):
        """Handle error in parsing - return safe fallback"""
        return {
            "signal": "HOLD",
            "confidence": 0.5,
            "expected_profit": 0,
            "risk_level": "HIGH",
            "reasoning": f"Error parsing AI response for {stock_code}",
            "opening_drive": "",
            "volume_confirmation": "",
            "foreign_flow_note": "",
            "tick_index_note": "",
        }
