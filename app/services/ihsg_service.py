import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Optional


_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
})


class IHSGService:
    def fetch_ihsg_data(self, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(2 ** attempt)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EJKSE?range={period}&interval={interval}"
                r = _session.get(url, timeout=15)
                if r.status_code == 429:
                    if attempt < 2:
                        continue
                    return None
                r.raise_for_status()
                data = r.json()
                result = data["chart"]["result"]
                if not result:
                    return None
                result = result[0]
                timestamps = result["timestamp"]
                quotes = result["indicators"]["quote"][0]
                df = pd.DataFrame({
                    "Open": quotes["open"],
                    "High": quotes["high"],
                    "Low": quotes["low"],
                    "Close": quotes["close"],
                    "Volume": quotes["volume"],
                }, index=pd.to_datetime(timestamps, unit="s"))
                df.index.name = "Date"
                df = df.dropna()
                if df.empty:
                    return None
                return df
            except Exception:
                if attempt < 2:
                    continue
                return None
        return None

    def get_ihsg_summary(self) -> dict:
        df_1mo = self.fetch_ihsg_data(period="1mo")
        df_1y = self.fetch_ihsg_data(period="1y")
        now_iso = datetime.now().isoformat()

        if df_1mo is None or df_1mo.empty:
            return {"error": "Failed to fetch IHSG data", "last_updated": now_iso}

        df_1mo["MA20"] = df_1mo["Close"].rolling(window=20).mean()
        df_1mo["MA50"] = df_1mo["Close"].rolling(window=50).mean()

        latest = df_1mo.iloc[-1]
        prev = df_1mo.iloc[-2] if len(df_1mo) > 1 else latest

        current_price = float(round(latest["Close"], 2))
        change_pct = float(round(((latest["Close"] - prev["Close"]) / prev["Close"]) * 100, 2))

        ma20 = float(round(latest["MA20"], 2)) if pd.notna(latest["MA20"]) else None
        ma50 = float(round(latest["MA50"], 2)) if pd.notna(latest["MA50"]) else None
        trend = "Bullish" if (ma20 is not None and ma50 is not None and ma20 > ma50) else "Bearish"

        support = float(round(df_1mo["Low"].min(), 2))
        resistance = float(round(df_1mo["High"].max(), 2))

        avg_vol_5d = float(df_1mo["Volume"].tail(5).mean())
        avg_vol_20d = float(df_1mo["Volume"].tail(20).mean())
        volume_trend = "Increasing" if avg_vol_5d > avg_vol_20d else "Decreasing"

        weekly_change = None
        monthly_change = None
        if len(df_1mo) >= 5:
            weekly_change = float(round(((latest["Close"] - df_1mo.iloc[-5]["Close"]) / df_1mo.iloc[-5]["Close"]) * 100, 2))
        if len(df_1mo) >= 21:
            monthly_change = float(round(((latest["Close"] - df_1mo.iloc[-21]["Close"]) / df_1mo.iloc[-21]["Close"]) * 100, 2))

        ytd_change = None
        if df_1y is not None and not df_1y.empty:
            start_of_year = pd.Timestamp(datetime.now().year, 1, 1)
            ytd_data = df_1y[df_1y.index >= start_of_year]
            if len(ytd_data) >= 2:
                ytd_change = float(round(((ytd_data["Close"].iloc[-1] - ytd_data["Close"].iloc[0]) / ytd_data["Close"].iloc[0]) * 100, 2))

        return {
            "current_price": current_price,
            "change_pct": change_pct,
            "weekly_change": weekly_change,
            "monthly_change": monthly_change,
            "ytd_change": ytd_change,
            "ma20": ma20,
            "ma50": ma50,
            "trend": trend,
            "support": support,
            "resistance": resistance,
            "volume_trend": volume_trend,
            "last_updated": now_iso,
        }

    def get_historical_ihsg(self, days: int = 365) -> list[dict]:
        period_map = {365: "1y", 730: "2y", 1825: "5y"}
        if days <= 365:
            period = "1y"
        elif days <= 730:
            period = "2y"
        else:
            period = "5y"
        df = self.fetch_ihsg_data(period=period)
        if df is None or df.empty:
            return []
        if len(df) > days:
            df = df.tail(days)
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA50"] = df["Close"].rolling(window=50).mean()
        result = []
        for idx, row in df.iterrows():
            result.append({
                "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                "close": float(round(row["Close"], 2)),
                "ma20": float(round(row["MA20"], 2)) if pd.notna(row["MA20"]) else None,
                "ma50": float(round(row["MA50"], 2)) if pd.notna(row["MA50"]) else None,
            })
        return result
