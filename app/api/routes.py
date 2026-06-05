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
from app.services.ihsg_service import IHSGService
from app.services.relative_strength import calculate_relative_strength, calculate_all_relative_strength
from app.charts.chart_generator import generate_full_analysis_chart
from app.database import crud
from app.database.foreign_flow_models import (
    get_foreign_flow,
    get_accumulation_status,
    get_all_accumulation_status,
)
import pandas as pd

router = APIRouter(prefix="/api", tags=["api"])
_analysis_service = None


def get_analysis_service():
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service


class WatchlistRequest(BaseModel):
    stock_code: str
    user_id: Optional[int] = 1


class AnalyzeRequest(BaseModel):
    stock_code: str
    use_ai: Optional[bool] = True


@router.get("/health")
def health_check():
    return {"status": "ok", "message": "AI Stock Analyzer is running"}

@router.get("/ai/status")
def ai_status():
    from app.config import Config
    from openai import OpenAI
    result = {
        "provider": Config.AI_PROVIDER,
        "base_url": Config.NINE_ROUTER_BASE_URL,
        "model": Config.NINE_ROUTER_MODEL,
        "reachable": False,
        "responding": False,
        "error": None,
        "models_available": [],
    }
    try:
        client = OpenAI(api_key=Config.NINE_ROUTER_API_KEY, base_url=Config.NINE_ROUTER_BASE_URL)
        # Test reachability
        models = client.models.list()
        result["reachable"] = True
        result["models_available"] = [m.id for m in models.data[:10]]
        # Test chat completion
        resp = client.chat.completions.create(
            model=Config.NINE_ROUTER_MODEL,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=50,
            temperature=0.3,
        )
        choice = resp.choices[0]
        content = (choice.message.content or "").strip()
        reasoning = getattr(choice.message, "reasoning_content", None) or ""
        if not content and reasoning.strip():
            content = reasoning.strip()
        result["responding"] = bool(content)
        result["response_sample"] = content[:100] if content else "(empty)"
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


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
    analysis_service = get_analysis_service()
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


@router.get("/ihsg")
async def get_ihsg():
    data = IHSGService().get_ihsg_summary()
    return {"status": "ok", "data": data}


@router.get("/relative-strength/{code}")
async def get_relative_strength(code: str):
    data = calculate_relative_strength(code)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Relative strength data for {code} not found")
    return {"status": "ok", "data": data}


@router.get("/market-breadth")
async def get_market_breadth():
    data = calculate_all_relative_strength()
    return {"status": "ok", "data": data}


@router.get("/foreign-flow/{code}")
async def foreign_flow(code: str, days: int = Query(30, ge=1, le=365)):
    history = get_foreign_flow(code, days)
    accumulation = get_accumulation_status(code)
    return {
        "status": "ok",
        "data": {
            "history": history,
            "accumulation_status": accumulation,
        },
    }


@router.get("/foreign-flow/summary")
async def foreign_flow_summary():
    all_status = get_all_accumulation_status()
    top_accumulating = [s for s in all_status if s.get("status") == "accumulating"][:10]
    top_distributing = [s for s in all_status if s.get("status") == "distributing"][:10]
    return {
        "status": "ok",
        "data": {
            "top_accumulating": top_accumulating,
            "top_distributing": top_distributing,
            "total_tracked": len(all_status),
        },
    }
