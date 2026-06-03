import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.services.stock_service import STOCK_LIST, fetch_stock_data


def get_sector_performance():
    sector_map = {
        "BBCA": "Financials", "BBRI": "Financials", "BMRI": "Financials", "BBNI": "Financials",
        "TLKM": "Telecommunication", "EXCL": "Telecommunication", "TOWR": "Telecommunication",
        "ASII": "Automotive", "UNVR": "Consumer Goods", "HMSP": "Consumer Goods",
        "GGRM": "Consumer Goods", "INDF": "Consumer Goods", "ICBP": "Consumer Goods",
        "KLBF": "Healthcare", "CPIN": "Consumer Goods",
        "ADRO": "Energy", "ITMG": "Energy", "PTBA": "Energy", "MEDC": "Energy",
        "PGAS": "Energy",
        "SMGR": "Infrastructure", "INTP": "Infrastructure", "JSMR": "Infrastructure",
        "AKRA": "Energy",
    }

    sector_data = {}
    for code, sector in sector_map.items():
        try:
            data = fetch_stock_data(code, period="1mo")
            if data:
                df = data["history"]
                if len(df) >= 2:
                    change = ((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100
                    if sector not in sector_data:
                        sector_data[sector] = {"changes": [], "count": 0}
                    sector_data[sector]["changes"].append(change)
                    sector_data[sector]["count"] += 1
        except Exception:
            continue

    result = {}
    for sector, data in sector_data.items():
        if data["changes"]:
            result[sector] = {
                "performance": round(np.mean(data["changes"]), 2),
                "count": data["count"],
                "status": "Positive" if np.mean(data["changes"]) > 0 else "Negative",
            }

    return result


def get_market_summary():
    total = len(STOCK_LIST)
    up = 0
    down = 0
    total_volume = 0
    changes = []

    for code in STOCK_LIST.keys():
        try:
            data = fetch_stock_data(code, period="5d")
            if data:
                df = data["history"]
                if len(df) >= 2:
                    change = ((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100
                    changes.append(change)
                    total_volume += int(df["Volume"].iloc[-1])
                    if change > 0:
                        up += 1
                    elif change < 0:
                        down += 1
        except Exception:
            continue

    if changes:
        avg_change = np.mean(changes)
        std_change = np.std(changes)
        fear_greed = _calculate_fear_greed(up, down, avg_change, std_change)
    else:
        avg_change = 0
        fear_greed = {"index": 50, "label": "Neutral"}

    return {
        "total_stocks": total,
        "advancing": up,
        "declining": down,
        "unchanged": total - up - down,
        "avg_change": round(avg_change, 2),
        "total_volume": total_volume,
        "fear_greed": fear_greed,
        "timestamp": datetime.now().isoformat(),
    }


def _calculate_fear_greed(up, down, avg_change, std_change):
    total = up + down
    if total == 0:
        return {"index": 50, "label": "Neutral"}

    advance_ratio = up / total if total > 0 else 0.5

    score = advance_ratio * 100

    if avg_change > 0:
        score += min(15, abs(avg_change) * 2)
    else:
        score -= min(15, abs(avg_change) * 2)

    score = max(0, min(100, score))

    if score >= 75:
        label = "Extreme Greed"
    elif score >= 60:
        label = "Greed"
    elif score >= 40:
        label = "Neutral"
    elif score >= 25:
        label = "Fear"
    else:
        label = "Extreme Fear"

    return {"index": round(score), "label": label}


def get_market_sentiment():
    summary = get_market_summary()
    fg = summary["fear_greed"]

    if fg["index"] >= 60:
        sentiment = "Bullish"
        description = "Market menunjukkan sentimen positif"
    elif fg["index"] >= 40:
        sentiment = "Neutral"
        description = "Market dalam kondisi netral"
    else:
        sentiment = "Bearish"
        description = "Market menunjukkan sentimen negatif"

    return {
        "sentiment": sentiment,
        "description": description,
        "fear_greed": fg,
        "advancing": summary["advancing"],
        "declining": summary["declining"],
        "advance_decline_ratio": round(summary["advancing"] / max(1, summary["declining"]), 2),
    }
