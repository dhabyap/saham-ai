# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from dataclasses import asdict
from datetime import datetime
import os
import logging
import json

logger = logging.getLogger(__name__)

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
from app.ai.scoring_engine import ScoringEngine
from app.charts.chart_generator import generate_full_analysis_chart
from app.database import crud
from app.database.foreign_flow_models import (
    get_foreign_flow,
    get_accumulation_status,
    get_all_accumulation_status,
)
from app.services.treemap_service import get_treemap_data
from app.services.shareholder_service import (
    get_shareholders_by_stock,
    get_shareholder_portfolio,
    get_available_periods,
    get_top_shareholders,
    get_latest_period,
    period_has_data,
    upsert_shareholder,
    bulk_import,
    get_shareholder_graph_data, # Added for Task 1
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


@router.get("/broker-summary/suggest-upload")
def broker_suggest_upload():
    """Suggest stocks WITHOUT broker data that are interesting for upload."""
    from app.database.database import get_db
    from app.services.stock_service import STOCK_LIST, fetch_stock_data

    with get_db() as conn:
        with_data = set(
            r[0] for r in conn.execute(
                "SELECT DISTINCT stock_code FROM broker_summary"
            ).fetchall()
        )

    candidates = []
    for code in sorted(set(STOCK_LIST.keys()) - with_data):
        try:
            d = fetch_stock_data(code, period="5d")
            if not d:
                continue
            df = d["history"]
            if len(df) < 2:
                continue
            price = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg = ((price - prev) / prev) * 100
            vol = int(df["Volume"].iloc[-1])
            vol_ma = float(df["Volume"].iloc[-3]) if len(df) >= 3 else vol
            vol_ratio = vol / vol_ma if vol_ma > 0 else 1
            score = min(10, vol_ratio * 5) + (5 if chg > 1 else (3 if chg > 0 else 0))
            name = STOCK_LIST.get(code, "")
            reasons = []
            if chg > 3:
                reasons.append(f"naik {chg:.1f}%")
            elif chg > 0:
                reasons.append(f"naik {chg:.1f}%")
            if vol_ratio > 2:
                reasons.append("volume melonjak")
            elif vol_ratio > 1.2:
                reasons.append("volume di atas rata-rata")
            reasons.append("belum ada data broker")
            candidates.append({
                "stock_code": code, "name": name, "price": round(price, 0),
                "change_pct": round(chg, 2), "volume_ratio": round(vol_ratio, 1),
                "score": round(score, 0), "reason": ", ".join(reasons),
            })
        except Exception:
            continue
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"status": "ok", "suggestions": candidates[:6]}


@router.get("/shareholders/periods")
def shareholder_periods():
    """List available data periods + stats."""
    from app.services.shareholder_service import get_db
    periods = get_available_periods()
    latest = get_latest_period()
    # Stats for latest period
    stats = {"total_records": 0, "total_stocks": 0, "total_holders": 0}
    if latest:
        with get_db() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM shareholders WHERE data_period=?", (latest,))
            stats["total_records"] = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE data_period=?", (latest,))
            stats["total_stocks"] = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(DISTINCT shareholder_name) FROM shareholders WHERE data_period=?", (latest,))
            stats["total_holders"] = cur.fetchone()[0]
    return {
        "status": "ok",
        "periods": periods,
        "latest": latest,
        "stats": stats,
    }


@router.get("/stats/shareholders")
def shareholder_stats(period: Optional[str] = None):
    """Get aggregate stats for a period."""
    from app.services.shareholder_service import get_db
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM shareholders WHERE 1=1" + 
            (" AND data_period=?" if period else ""),
            (period,) if period else ())
        total = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE 1=1" + 
            (" AND data_period=?" if period else ""),
            (period,) if period else ())
        stocks = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(DISTINCT shareholder_name) FROM shareholders WHERE 1=1" + 
            (" AND data_period=?" if period else ""),
            (period,) if period else ())
        holders = cur.fetchone()[0]
        # Top holder name
        top_sql = """SELECT shareholder_name, SUM(share_percent) as total 
            FROM shareholders WHERE 1=1"""
        if period:
            top_sql += " AND data_period=?"
        top_sql += " GROUP BY shareholder_name ORDER BY total DESC LIMIT 1"
        cur = conn.execute(top_sql, (period,) if period else ())
        top = cur.fetchone()
    return {
        "status": "ok",
        "total_records": total,
        "total_stocks": stocks,
        "total_holders": holders,
        "top_holder": top[0] if top else "-",
        "period": period or "all",
    }


@router.get("/shareholders/top")
def shareholder_top(
    limit: int = Query(20, ge=1, le=100),
    period: Optional[str] = None,
    min_pct: float = Query(1.0, ge=0.1, le=100),
):
    """Top individual shareholders across all stocks."""
    return {
        "status": "ok",
        "period": period or "latest",
        "data": get_top_shareholders(limit, period, min_pct),
    }


@router.get("/shareholders/bubble-data")
def shareholder_bubble_data(period: Optional[str] = None):
    """Bubble chart data: top shareholders with has_majority flag (any holding >=5%)."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            if period:
                rows = conn.execute("""
                    SELECT shareholder_name, COUNT(*) as stock_count,
                           ROUND(SUM(share_percent), 2) as total_pct,
                           MAX(CASE WHEN share_percent >= 5 THEN 1 ELSE 0 END) as has_majority
                    FROM shareholders
                    WHERE data_period = ? AND share_percent >= 0.5
                    GROUP BY shareholder_name
                    HAVING total_pct >= 1
                    ORDER BY total_pct DESC
                    LIMIT 80
                """, (period,))
            else:
                rows = conn.execute("""
                    SELECT shareholder_name, COUNT(*) as stock_count,
                           ROUND(SUM(share_percent), 2) as total_pct,
                           MAX(CASE WHEN share_percent >= 5 THEN 1 ELSE 0 END) as has_majority
                    FROM shareholders
                    WHERE share_percent >= 0.5
                    GROUP BY shareholder_name
                    HAVING total_pct >= 1
                    ORDER BY total_pct DESC
                    LIMIT 80
                """)
            data = []
            for r in rows:
                d = dict(r)
                d["has_majority"] = bool(d["has_majority"])
                data.append(d)
            return {"status": "ok", "data": data}
    except Exception as e:
        logger.error("bubble-data error: %s", e)
        return {"status": "error", "data": [], "error": str(e)}


@router.get("/shareholders/network-data")
def shareholder_network_data(period: Optional[str] = None):
    """Force-directed graph data: top shareholders + their stock connections."""
    try:
        graph_data = get_shareholder_graph_data(period=period)
        return {"status": "ok", **graph_data}
    except Exception as e:
        logger.error("network-data error: %s", e)
        return {"status": "error", "nodes": [], "edges": [], "error": str(e)}


@router.get("/shareholders/stocks")
def shareholder_stocks(period: Optional[str] = None):
    """List stocks that have shareholder data (with name if known)."""
    try:
        from app.services.shareholder_service import get_db
        from app.services.stock_service import STOCK_LIST
        with get_db() as conn:
            if period:
                rows = conn.execute(
                    """SELECT stock_code, COUNT(*) as holder_count, SUM(share_percent) as total_pct
                       FROM shareholders
                       WHERE data_period = ?
                       GROUP BY stock_code
                       ORDER BY stock_code ASC""",
                    (period,)
                )
            else:
                rows = conn.execute(
                    """SELECT stock_code, COUNT(*) as holder_count, SUM(share_percent) as total_pct
                       FROM shareholders
                       GROUP BY stock_code
                       ORDER BY stock_code ASC"""
                )
            result = []
            for r in rows:
                d = dict(r)
                d["stock_name"] = STOCK_LIST.get(d["stock_code"], "")
                result.append(d)
            return {"status": "ok", "period": period or "all", "data": result}
    except Exception as e:
        import traceback
        logger.error("shareholder_stocks error: %s\n%s", e, traceback.format_exc())
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.get("/shareholders/search/{name}")
def shareholder_search(name: str, period: Optional[str] = None):
    """Search portfolio of a specific shareholder (e.g. 'LO KHENG HONG')."""
    return {
        "status": "ok",
        "shareholder_name": name,
        "period": period or "latest",
        "data": get_shareholder_portfolio(name, period),
    }


@router.post("/shareholders/import")
async def import_shareholders(
    file: UploadFile = File(...),
    data_period: str = Form(..., description="Format YYYYMMDD, e.g., 20240131"),
):
    """Import shareholder data from CSV or Excel file."""
    try:
        contents = await file.read()
        df = None
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(400, "Unsupported file type. Please upload CSV or Excel.")

        rows = df.to_dict(orient='records')
        
        # Convert all keys to lowercase for case-insensitive matching
        rows_lower = [{k.lower(): v for k, v in row.items()} for row in rows]

        # Map column names to expected service fields
        mapped_rows = []
        for row in rows_lower:
            mapped_rows.append({
                "stock_code": row.get("stock_code", row.get("kode_saham")),
                "shareholder_name": row.get("shareholder_name", row.get("nama_pemegang_saham")),
                "share_percent": row.get("share_percent", row.get("persentase_saham", row.get("persen_saham"))),
                "share_count": row.get("share_count", row.get("jumlah_saham", row.get("saham"))),
                "category": row.get("category", row.get("kategori")),
            })

        # Filter out rows with missing essential data
        final_rows = []
        for i, row in enumerate(mapped_rows):
            stock_code = row.get("stock_code")
            shareholder_name = row.get("shareholder_name")
            share_percent = row.get("share_percent")

            if not stock_code or not shareholder_name or share_percent is None:
                logger.warning(f"Skipping row {i} due to missing stock_code, shareholder_name, or share_percent: {row}")
                continue
            
            try:
                row["share_percent"] = float(row["share_percent"])
            except ValueError:
                logger.warning(f"Skipping row {i} due to invalid share_percent: {row['share_percent']}")
                continue
            
            final_rows.append(row)
        
        if not final_rows:
            raise HTTPException(400, "No valid data found after processing file. Check column names (stock_code, shareholder_name, share_percent).")

        result = bulk_import(final_rows, data_period)
        return {"status": "ok", "message": "Import successful", **result}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Error importing shareholder data: %s", e)
        raise HTTPException(500, f"Failed to import data: {e}")


@router.post("/shareholders/upload-json")
async def upload_shareholder_json(
    data: dict,
    data_period: str = Query(..., description="Format YYYYMMDD, e.g., 20240131"),
):
    """Upload shareholder data directly as JSON."""
    if not isinstance(data, list):
        raise HTTPException(400, "JSON data must be a list of records.")

    # Process JSON data, similar to bulk_import
    mapped_rows = []
    for row in data:
        # Convert keys to lowercase for robust matching
        row_lower = {k.lower(): v for k, v in row.items()}
        mapped_rows.append({
            "stock_code": row_lower.get("stock_code", row_lower.get("kode_saham")),
            "shareholder_name": row_lower.get("shareholder_name", row_lower.get("nama_pemegang_saham")),
            "share_percent": row_lower.get("share_percent", row_lower.get("persentase_saham", row_lower.get("persen_saham"))),
            "share_count": row_lower.get("share_count", row_lower.get("jumlah_saham", row_lower.get("saham"))),
            "category": row_lower.get("category", row_lower.get("kategori")),
        })
    
    final_rows = []
    for i, row in enumerate(mapped_rows):
        stock_code = row.get("stock_code")
        shareholder_name = row.get("shareholder_name")
        share_percent = row.get("share_percent")

        if not stock_code or not shareholder_name or share_percent is None:
            logger.warning(f"Skipping row {i} due to missing stock_code, shareholder_name, or share_percent in JSON: {row}")
            continue
        
        try:
            row["share_percent"] = float(row["share_percent"])
        except ValueError:
            logger.warning(f"Skipping row {i} due to invalid share_percent in JSON: {row['share_percent']}")
            continue
        
        final_rows.append(row)

    if not final_rows:
        raise HTTPException(400, "No valid data found in JSON after processing. Check column names.")

    result = bulk_import(final_rows, data_period)
    return {"status": "ok", "message": "Import successful", **result}


@router.get("/admin/db/reset-shareholders")
def reset_shareholders_db():
    from app.database.database import get_db
    with get_db() as conn:
        conn.execute("DROP TABLE IF EXISTS shareholders")
        # Re-init table (this will be done by the next call to any shareholder service)
    return {"status": "ok", "message": "Shareholders table reset. It will be re-initialized on next data access."}


@router.get("/charts/full-analysis/{stock_code}")
async def get_full_analysis_chart(stock_code: str):
    """Generate a full analysis chart for a given stock code."""
    try:
        chart_path = generate_full_analysis_chart(stock_code)
        if chart_path and os.path.exists(chart_path):
            return FileResponse(chart_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Chart not found")
    except Exception as e:
        logger.error(f"Error generating full analysis chart for {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chart: {e}")


@router.get("/treemap/{category}")
def get_treemap_categories(category: str):
    """Retrieve treemap data for a specific category (e.g., sector, market_cap)."""
    data = get_treemap_data(category)
    return {"status": "ok", "data": data}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook for bot updates."""
    # This endpoint is handled by the python-telegram-bot library internally
    # when the bot is running. We just need to define it for FastAPI.
    return {"status": "ok", "message": "Webhook received, processed by bot."}
