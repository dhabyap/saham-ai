from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os

from app.services.stock_service import (
    get_latest_data,
    get_top_gainers,
    get_top_losers,
    get_top_volume,
    STOCK_LIST,
)
from app.services.analysis_service import AnalysisService
from app.services.market_service import (
    get_market_summary,
    get_market_sentiment,
    get_sector_performance,
)
from app.charts.chart_generator import generate_full_analysis_chart
from app.database import crud
import pandas as pd

router = APIRouter(prefix="/api", tags=["api"])
analysis_service = AnalysisService()


class WatchlistRequest(BaseModel):
    stock_code: str
    user_id: Optional[int] = 1


class AnalyzeRequest(BaseModel):
    stock_code: str
    use_ai: Optional[bool] = True


@router.get("/health")
def health_check():
    return {"status": "ok", "message": "AI Stock Analyzer is running"}


@router.get("/stock/{code}")
def get_stock(code: str, period: str = Query("3mo", description="Period: 1mo, 3mo, 6mo, 1y")):
    data = get_latest_data(code, period=period)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Data for {code} not found")

    df = data.pop("dataframe", None)
    history = None
    if df is not None:
        history = []
        for idx, row in df.iterrows():
            try:
                history.append({
                    "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })
            except Exception:
                continue
        data["history"] = history[-60:] if history else []

    return data


@router.get("/analyze/{code}")
def analyze_stock(code: str):
    result = analysis_service.analyze_stock(code, use_ai=True)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    df = result.pop("dataframe", None)
    history = None
    if df is not None:
        history = []
        for idx, row in df.iterrows():
            try:
                history.append({
                    "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                    "ma20": round(row["MA20"], 2) if "MA20" in row and not pd.isna(row["MA20"]) else None,
                    "ma50": round(row["MA50"], 2) if "MA50" in row and not pd.isna(row["MA50"]) else None,
                    "rsi": round(row["RSI"], 2) if "RSI" in row and not pd.isna(row["RSI"]) else None,
                })
            except Exception:
                continue
        result["history"] = history[-60:]

    return result


@router.get("/chart/{code}")
def get_chart(code: str):
    data = get_latest_data(code)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Data for {code} not found")

    df = data.get("dataframe")
    if df is None:
        raise HTTPException(status_code=404, detail="No chart data available")

    chart_path = generate_full_analysis_chart(df, data["stock_code"], data.get("stock_name", ""))
    if chart_path and os.path.exists(chart_path):
        return FileResponse(chart_path, media_type="image/png")

    raise HTTPException(status_code=500, detail="Failed to generate chart")


@router.get("/market-summary")
def market_summary():
    return get_market_summary()


@router.get("/market-sentiment")
def market_sentiment():
    return get_market_sentiment()


@router.get("/sector-performance")
def sector_performance():
    return get_sector_performance()


@router.get("/top-gainers")
def top_gainers(limit: int = Query(10, ge=1, le=30)):
    return {"gainers": get_top_gainers(limit)}


@router.get("/top-losers")
def top_losers(limit: int = Query(10, ge=1, le=30)):
    return {"losers": get_top_losers(limit)}


@router.get("/top-volume")
def top_volume(limit: int = Query(10, ge=1, le=30)):
    return {"volumes": get_top_volume(limit)}


@router.get("/stocks")
def list_stocks():
    stocks = [{"code": k, "name": v} for k, v in STOCK_LIST.items()]
    return {"stocks": stocks}


@router.post("/watchlist/add")
def add_watchlist(req: WatchlistRequest):
    user = crud.get_user(req.user_id)
    if not user:
        user = crud.add_user(req.user_id)

    crud.add_to_watchlist(user["id"], req.stock_code, STOCK_LIST.get(req.stock_code.upper(), ""))
    return {"status": "ok", "message": f"{req.stock_code.upper()} added to watchlist"}


@router.post("/watchlist/remove")
def remove_watchlist(req: WatchlistRequest):
    user = crud.get_user(req.user_id)
    if user:
        crud.remove_from_watchlist(user["id"], req.stock_code)

    return {"status": "ok", "message": f"{req.stock_code.upper()} removed from watchlist"}


@router.get("/watchlist/{user_id}")
def get_watchlist(user_id: int):
    user = crud.get_user(user_id)
    if not user:
        return {"watchlist": []}

    items = crud.get_watchlist(user["id"])
    return {"watchlist": items}


@router.get("/analysis-history")
def analysis_history(limit: int = Query(20, ge=1, le=100)):
    history = crud.get_recent_analysis(limit)
    return {"history": history}


@router.get("/alerts")
def get_alerts(limit: int = Query(20, ge=1, le=100)):
    alerts = crud.get_alerts(limit)
    return {"alerts": alerts}
