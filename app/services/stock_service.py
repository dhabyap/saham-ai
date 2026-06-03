import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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


def get_stock_code(code):
    code = code.upper().strip()
    if not code.endswith(".JK"):
        code = f"{code}.JK"
    return code


def fetch_stock_data(code, period="3mo", interval="1d"):
    try:
        ticker = yf.Ticker(get_stock_code(code))
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        info = ticker.info if ticker.info else {}
        return {"history": df, "info": info}
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return None


def calculate_indicators(df):
    if df is None or df.empty:
        return None

    df = df.copy()

    # MA20 & MA50
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Volume MA
    df["Volume_MA"] = df["Volume"].rolling(window=20).mean()

    # Support & Resistance sederhana
    df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["R1"] = 2 * df["Pivot"] - df["Low"]
    df["S1"] = 2 * df["Pivot"] - df["High"]

    return df


def get_latest_data(code, period="3mo"):
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
    volume_spike = volume_ratio > 1.5

    # Support/Resistance break
    price = latest["Close"]
    near_resistance = abs(price - resistance) / price < 0.02 if resistance > 0 else False
    near_support = abs(price - support) / price < 0.02 if support > 0 else False

    # Overbought/Oversold
    rsi_val = latest["RSI"]
    if pd.notna(rsi_val):
        if rsi_val > 70:
            rsi_status = "Overbought"
        elif rsi_val < 30:
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

    return result


def get_top_gainers(limit=10):
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


def get_top_losers(limit=10):
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


def get_top_volume(limit=10):
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
