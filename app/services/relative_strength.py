import pandas as pd
from datetime import datetime
from typing import Optional

from app.services.stock_service import fetch_stock_data, STOCK_LIST
from app.services.ihsg_service import IHSGService


def calculate_relative_strength(stock_code: str, period_days: int = 63) -> Optional[dict]:
    stock_data = fetch_stock_data(stock_code, period="6mo")
    ihsg_data = IHSGService().fetch_ihsg_data(period="6mo")
    now_iso = datetime.now().isoformat()

    if stock_data is None or ihsg_data is None:
        return None

    stock_df = stock_data["history"]
    ihsg_df = ihsg_data

    combined = stock_df[["Close"]].join(ihsg_df[["Close"]], how="inner", lsuffix="_stock", rsuffix="_ihsg")

    if combined.empty or len(combined) < period_days:
        return None

    latest_stock_close = float(combined["Close_stock"].iloc[-1])
    past_stock_close = float(combined["Close_stock"].iloc[-period_days])
    stock_return = ((latest_stock_close - past_stock_close) / past_stock_close) * 100

    latest_ihsg_close = float(combined["Close_ihsg"].iloc[-1])
    past_ihsg_close = float(combined["Close_ihsg"].iloc[-period_days])
    ihsg_return = ((latest_ihsg_close - past_ihsg_close) / past_ihsg_close) * 100

    rs_value = round(stock_return - ihsg_return, 2)

    if rs_value > 5:
        rs_status = "Outperforming"
    elif rs_value < -5:
        rs_status = "Underperforming"
    else:
        rs_status = "Neutral"

    return {
        "stock_code": stock_code.upper().replace(".JK", ""),
        "stock_return_pct": round(stock_return, 2),
        "ihsg_return_pct": round(ihsg_return, 2),
        "rs_value": rs_value,
        "rs_status": rs_status,
        "period_days": period_days,
        "last_updated": now_iso,
    }


def calculate_all_relative_strength() -> dict:
    outperformers = []
    underperformers = []
    neutral = []

    for code in STOCK_LIST:
        result = calculate_relative_strength(code)
        if result is None:
            continue
        entry = {
            "stock_code": result["stock_code"],
            "stock_name": STOCK_LIST.get(result["stock_code"], ""),
            "stock_return_pct": result["stock_return_pct"],
            "ihsg_return_pct": result["ihsg_return_pct"],
            "rs_value": result["rs_value"],
            "rs_status": result["rs_status"],
        }
        if result["rs_status"] == "Outperforming":
            outperformers.append(entry)
        elif result["rs_status"] == "Underperforming":
            underperformers.append(entry)
        else:
            neutral.append(entry)

    outperformers.sort(key=lambda x: x["rs_value"], reverse=True)
    underperformers.sort(key=lambda x: x["rs_value"])
    neutral.sort(key=lambda x: x["rs_value"], reverse=True)

    return {
        "outperformers": outperformers,
        "underperformers": underperformers,
        "neutral": neutral,
        "counts": {
            "outperformers": len(outperformers),
            "underperformers": len(underperformers),
            "neutral": len(neutral),
        },
        "total_analyzed": len(outperformers) + len(underperformers) + len(neutral),
        "last_updated": datetime.now().isoformat(),
    }
