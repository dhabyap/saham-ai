import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Optional

from app.constants import (
    USER_AGENT, HEADERS, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    MA_SHORT, MA_LONG, VOLUME_SPIKE_THRESHOLD, SUPPORT_RESISTANCE_PROXIMITY,
    RSI_OVERBOUGHT, RSI_OVERSOLD, OPENING_RANGE_MINUTES,
)
from app.http_client import get_http_client
from app.database.foreign_flow_models import get_accumulation_status, get_foreign_flow


STOCK_LIST = {
    "BBCA": "PT Bank Central Asia Tbk",
    "BBRI": "PT Bank Rakyat Indonesia Tbk",
    "BMRI": "PT Bank Mandiri Tbk",
    "BBNI": "PT Bank Negara Indonesia Tbk",
    "TLKM": "PT Telkom Indonesia Tbk",
    "ASII": "PT Astra International Tbk",
    "UNVR": "PT Unilever Indonesia Tbk",
    "HMSP": "PT Hanjaya Mandala Sampoerna Tbk",
    "GGRM": "PT Gudang Garam Tbk",
    "INDF": "PT Indofood Sukses Makmur Tbk",
    "ADRO": "PT Adaro Energy Indonesia Tbk",
    "ITMG": "PT Indo Tambangraya Megah Tbk",
    "PTBA": "PT Bukit Asam Tbk",
    "CPIN": "PT Charoen Pokphand Indonesia Tbk",
    "KLBF": "PT Kalbe Farma Tbk",
    "ICBP": "PT Indofood CBP Sukses Makmur Tbk",
    "JSMR": "PT Jasa Marga Tbk",
    "PGAS": "PT Perusahaan Gas Negara Tbk",
    "EXCL": "PT XL Axiata Tbk",
    "TOWR": "PT Sarana Menara Nusantara Tbk",
    "SMGR": "PT Semen Indonesia Tbk",
    "INTP": "PT Indocement Tunggal Prakarsa Tbk",
    "SMMA": "PT Sinar Mas Multiartha Tbk",
    "AKRA": "PT AKR Corporindo Tbk",
    "MEDC": "PT Medco Energi Internasional Tbk",
}


def get_stock_code(code: str) -> str:
    code = code.upper().strip()
    if not code.endswith(".JK"):
        code = f"{code}.JK"
    return code


_session = get_http_client()

PERIOD_MAP = {
    "1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo",
    "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y", "max": "max",
}

def fetch_stock_data(code: str, period: str = "3mo", interval: str = "1d", max_retries: int = 3) -> Optional[dict]:
    period = PERIOD_MAP.get(period, "3mo")
    code = get_stock_code(code).upper()

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(2 ** attempt)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}?range={period}&interval={interval}"
            r = _session.get(url, timeout=15)
            if r.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"  ⏳ Rate limited for {code}, retrying in {2 ** attempt}s...")
                    continue
                print(f"Error fetching {code}: rate limited (429)")
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
            return {"history": df, "info": {}}
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            print(f"Error fetching {code}: {e}")
            return None
    return None


def calculate_indicators(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None

    df = df.copy()

    # MA20 & MA50
    df["MA20"] = df["Close"].rolling(window=MA_SHORT).mean()
    df["MA50"] = df["Close"].rolling(window=MA_LONG).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=RSI_PERIOD).mean()
    avg_loss = loss.rolling(window=RSI_PERIOD).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=MACD_FAST, adjust=False).mean()
    ema26 = df["Close"].ewm(span=MACD_SLOW, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Volume MA
    df["Volume_MA"] = df["Volume"].rolling(window=MA_SHORT).mean()

    # Support & Resistance sederhana
    df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["R1"] = 2 * df["Pivot"] - df["Low"]
    df["S1"] = 2 * df["Pivot"] - df["High"]

    return df


def get_latest_data(code: str, period: str = "3mo") -> Optional[dict]:
    data = fetch_stock_data(code, period=period)
    if data is None:
        return None

    df = calculate_indicators(data["history"])
    if df is None or df.empty:
        return None

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    volume_ratio = latest["Volume"] / latest["Volume_MA"] if latest["Volume_MA"] > 0 else 1

    # Support & Resistance
    support = df["S1"].iloc[-1]
    resistance = df["R1"].iloc[-1]

    # Trend detection
    ma20 = latest["MA20"]
    ma50 = latest["MA50"]
    if pd.notna(ma20) and pd.notna(ma50):
        if latest["Close"] > ma20 and ma20 > ma50:
            trend = "Bullish"
        elif latest["Close"] < ma20 and ma20 < ma50:
            trend = "Bearish"
        elif latest["Close"] > ma20:
            trend = "Bullish (short term)"
        elif latest["Close"] < ma20:
            trend = "Bearish (short term)"
        else:
            trend = "Sideways"
    else:
        trend = "Sideways"

    # MACD signal
    macd_val = latest["MACD"]
    macd_signal = latest["MACD_Signal"]
    if pd.notna(macd_val) and pd.notna(macd_signal):
        if macd_val > macd_signal and prev["MACD"] <= prev["MACD_Signal"]:
            macd_status = "Golden Cross"
        elif macd_val < macd_signal and prev["MACD"] >= prev["MACD_Signal"]:
            macd_status = "Death Cross"
        elif macd_val > macd_signal:
            macd_status = "Bullish"
        else:
            macd_status = "Bearish"
    else:
        macd_status = "N/A"

    # Volume spike
    volume_spike = bool(volume_ratio > VOLUME_SPIKE_THRESHOLD)

    # Support/Resistance break
    price = latest["Close"]
    near_resistance = bool(abs(price - resistance) / price < SUPPORT_RESISTANCE_PROXIMITY) if resistance > 0 else False
    near_support = bool(abs(price - support) / price < SUPPORT_RESISTANCE_PROXIMITY) if support > 0 else False

    # Overbought/Oversold
    rsi_val = latest["RSI"]
    if pd.notna(rsi_val):
        if rsi_val > RSI_OVERBOUGHT:
            rsi_status = "Overbought"
        elif rsi_val < RSI_OVERSOLD:
            rsi_status = "Oversold"
        else:
            rsi_status = "Normal"
    else:
        rsi_status = "N/A"

    result = {
        "stock_code": code.upper(),
        "stock_name": STOCK_LIST.get(code.upper().replace(".JK", ""), ""),
        "price": round(price, 2),
        "open": round(latest["Open"], 2),
        "high": round(latest["High"], 2),
        "low": round(latest["Low"], 2),
        "volume": int(latest["Volume"]),
        "change": round(price - prev["Close"], 2),
        "change_pct": round(((price - prev["Close"]) / prev["Close"]) * 100, 2),
        "ma20": round(ma20, 2) if pd.notna(ma20) else None,
        "ma50": round(ma50, 2) if pd.notna(ma50) else None,
        "rsi": round(rsi_val, 2) if pd.notna(rsi_val) else None,
        "rsi_status": rsi_status,
        "macd": round(macd_val, 4) if pd.notna(macd_val) else None,
        "macd_signal": round(macd_signal, 4) if pd.notna(macd_signal) else None,
        "macd_histogram": round(latest["MACD_Hist"], 4) if pd.notna(latest.get("MACD_Hist")) else None,
        "macd_status": macd_status,
        "trend": trend,
        "support": round(support, 2) if pd.notna(support) else None,
        "resistance": round(resistance, 2) if pd.notna(resistance) else None,
        "volume_ratio": round(volume_ratio, 2),
        "volume_spike": volume_spike,
        "near_resistance": near_resistance,
        "near_support": near_support,
        "volume_avg": round(latest["Volume_MA"], 0) if pd.notna(latest["Volume_MA"]) else None,
        "dataframe": df,
    }

    # Inject foreign flow & accumulation data
    clean_code = code.upper().replace(".JK", "")
    try:
        accum = get_accumulation_status(clean_code)
        if accum:
            result["accumulation_days"] = accum.get("accumulation_days", 0)
            result["distribution_days"] = accum.get("distribution_days", 0)
            result["accumulation_status"] = accum.get("status", "neutral")
            result["accumulation_strength"] = accum.get("strength", "weak")
            result["accumulation_cumulative_net"] = round(accum.get("cumulative_net", 0), 0)

        flow = get_foreign_flow(clean_code, days=5)
        if flow:
            result["foreign_net_buy"] = round(sum(r.get("foreign_net", 0) for r in flow), 0)
            result["foreign_buy_total"] = round(sum(r.get("foreign_buy", 0) for r in flow), 0)
            result["foreign_sell_total"] = round(sum(r.get("foreign_sell", 0) for r in flow), 0)
            result["foreign_flow_days"] = len(flow)
        else:
            result["foreign_net_buy"] = 0
            result["foreign_flow_days"] = 0
    except Exception:
        result["foreign_net_buy"] = 0
        result["accumulation_days"] = 0
        result["foreign_flow_days"] = 0

    # Convert numpy types to native Python for JSON serialization
    for k, v in result.items():
        if k == "dataframe":
            continue
        if isinstance(v, (np.integer,)):
            result[k] = int(v)
        elif isinstance(v, (np.floating,)):
            result[k] = float(v)
        elif isinstance(v, (np.bool_,)):
            result[k] = bool(v)

    return result


VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m"}


def fetch_intraday_data(code: str, interval: str = "5m", period: str = "2d", max_retries: int = 3) -> Optional[pd.DataFrame]:
    if interval not in VALID_INTERVALS:
        print(f"Invalid interval: {interval}. Using 5m.")
        interval = "5m"
    code = get_stock_code(code).upper()

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(2 ** attempt)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}?range={period}&interval={interval}"
            r = _session.get(url, timeout=15)
            if r.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"  ⏳ Rate limited for {code}, retrying in {2 ** attempt}s...")
                    continue
                print(f"Error fetching {code}: rate limited (429)")
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
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            print(f"Error fetching intraday {code}: {e}")
            return None
    return None


def get_opening_range(df: pd.DataFrame, interval: str = "5m") -> dict:
    if df is None or df.empty:
        return {"error": "No data"}

    today = pd.Timestamp.now().normalize()
    today_df = df[df.index.normalize() == today]

    if today_df.empty:
        return {"error": "Market closed — no intraday data for today"}
    if len(today_df) < 2:
        return {"error": "Market baru buka — data belum cukup"}

    interval_minutes = int(interval.replace("m", ""))
    opening_rows = max(1, OPENING_RANGE_MINUTES // interval_minutes)
    opening_df = today_df.iloc[:opening_rows]
    if opening_df.empty:
        return {"error": "Opening range not available yet"}

    first_open = opening_df["Open"].iloc[0]
    open_range_high = float(opening_df["High"].max())
    open_range_low = float(opening_df["Low"].min())
    open_range_mid = (open_range_high + open_range_low) / 2
    range_size = open_range_high - open_range_low
    range_pct = (range_size / first_open * 100) if first_open != 0 else 0

    first_30min_volume = int(opening_df["Volume"].sum())
    total_volume = int(today_df["Volume"].sum())
    total_rows = len(today_df)
    avg_per_row_volume = total_volume / total_rows if total_rows > 0 else 1
    volume_ratio = first_30min_volume / (avg_per_row_volume * opening_rows) if avg_per_row_volume > 0 else 1

    gap_pct = 0.0
    if len(today_df) > opening_rows:
        first_candle_open = today_df["Open"].iloc[0]
        second_candle_open = today_df["Open"].iloc[1]
        if second_candle_open != 0:
            gap_pct = (first_candle_open - second_candle_open) / second_candle_open * 100
    if len(today_df) >= 2:
        prev_close = today_df["Close"].iloc[0]
        if prev_close != 0:
            gap_pct = (first_open - prev_close) / prev_close * 100

    return {
        "open_range_high": round(open_range_high, 2),
        "open_range_low": round(open_range_low, 2),
        "open_range_mid": round(open_range_mid, 2),
        "range_pct": round(range_pct, 2),
        "gap_pct": round(gap_pct, 2),
        "first_30min_volume": first_30min_volume,
        "volume_ratio": round(volume_ratio, 2),
        "first_open": round(first_open, 2),
    }


def get_top_gainers(limit: int = 10) -> list:
    results = []
    for code in list(STOCK_LIST.keys())[:30]:
        try:
            data = fetch_stock_data(code, period="5d")
            if data:
                df = data["history"]
                if len(df) >= 2:
                    change = ((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100
                    results.append({
                        "code": code,
                        "name": STOCK_LIST[code],
                        "price": round(df["Close"].iloc[-1], 2),
                        "change_pct": round(change, 2),
                    })
        except Exception:
            continue

    results.sort(key=lambda x: x["change_pct"], reverse=True)
    return results[:limit]


def get_top_losers(limit: int = 10) -> list:
    results = []
    for code in list(STOCK_LIST.keys())[:30]:
        try:
            data = fetch_stock_data(code, period="5d")
            if data:
                df = data["history"]
                if len(df) >= 2:
                    change = ((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100
                    results.append({
                        "code": code,
                        "name": STOCK_LIST[code],
                        "price": round(df["Close"].iloc[-1], 2),
                        "change_pct": round(change, 2),
                    })
        except Exception:
            continue

    results.sort(key=lambda x: x["change_pct"])
    return results[:limit]


def get_top_volume(limit: int = 10) -> list:
    results = []
    for code in list(STOCK_LIST.keys())[:30]:
        try:
            data = fetch_stock_data(code, period="5d")
            if data:
                df = data["history"]
                if len(df) >= 2:
                    results.append({
                        "code": code,
                        "name": STOCK_LIST[code],
                        "price": round(df["Close"].iloc[-1], 2),
                        "volume": int(df["Volume"].iloc[-1]),
                    })
        except Exception:
            continue

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:limit]
