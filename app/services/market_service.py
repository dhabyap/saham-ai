import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

from app.constants import SECTOR_MAP, MARKET_FLOW_INFLOW, MARKET_FLOW_OUTFLOW, FEAR_GREED_STRONG, FEAR_GREED_MODERATE
from app.services.stock_service import STOCK_LIST, fetch_stock_data


def get_sector_performance() -> dict:
    sector_data = {}
    for code, sector in SECTOR_MAP.items():
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
            perf = round(np.mean(data["changes"]), 2)
            result[sector] = {
                "performance": perf,
                "count": data["count"],
                "status": "Positive" if perf > 0 else "Negative",
                "flow": "INFLOW" if perf > MARKET_FLOW_INFLOW else ("OUTFLOW" if perf < MARKET_FLOW_OUTFLOW else "NEUTRAL"),
            }

    # Update global sector flow cache
    global SECTOR_FLOW
    SECTOR_FLOW = result

    return result

def get_sector_flow() -> dict:
    """Get sector rotation flow summary for AI context"""
    if not SECTOR_FLOW:
        get_sector_performance()
    
    inflow_sectors = [s for s, d in SECTOR_FLOW.items() if d.get("flow") == "INFLOW"]
    outflow_sectors = [s for s, d in SECTOR_FLOW.items() if d.get("flow") == "OUTFLOW"]
    
    return {
        "inflow_sectors": inflow_sectors[:3],
        "outflow_sectors": outflow_sectors[:3],
        "top_sector": max(SECTOR_FLOW, key=lambda s: SECTOR_FLOW[s]["performance"]) if SECTOR_FLOW else None,
        "worst_sector": min(SECTOR_FLOW, key=lambda s: SECTOR_FLOW[s]["performance"]) if SECTOR_FLOW else None,
    }


def get_market_summary() -> dict:
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


def _calculate_fear_greed(up: int, down: int, avg_change: float, std_change: float) -> dict:
    total = up + down
    if total == 0:
        return {"index": 50, "label": "Neutral"}

    advance_ratio = up / total if total > 0 else 0.5

    score = advance_ratio * 100

    if avg_change > 0:
        score += min(FEAR_GREED_MODERATE, abs(avg_change) * 2)
    else:
        score -= min(FEAR_GREED_MODERATE, abs(avg_change) * 2)

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


def get_market_sentiment() -> dict:
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
