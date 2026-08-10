# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
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
@router.get("/shareholders/force-graph")
def shareholder_force_graph(period: Optional[str] = None):
    """Force-directed graph: top shareholders + their stock connections."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            if period:
                rows = conn.execute("""
                    SELECT shareholder_name, COUNT(*) as stock_count,
                           ROUND(SUM(share_percent), 2) as total_pct
                    FROM shareholders
                    WHERE data_period = ? AND share_percent >= 0.5
                    GROUP BY shareholder_name
                    HAVING total_pct >= 1
                    ORDER BY total_pct DESC
                    LIMIT 40
                """, (period,))
            else:
                rows = conn.execute("""
                    SELECT shareholder_name, COUNT(*) as stock_count,
                           ROUND(SUM(share_percent), 2) as total_pct
                    FROM shareholders
                    WHERE share_percent >= 0.5
                    GROUP BY shareholder_name
                    HAVING total_pct >= 1
                    ORDER BY total_pct DESC
                    LIMIT 40
                """)
            top_holders = [dict(r) for r in rows]
            if not top_holders:
                return {"status": "ok", "nodes": [], "edges": []}

            holder_names = [h["shareholder_name"] for h in top_holders]
            placeholders = ",".join("?" for _ in holder_names)
            name_upper = [n.upper() for n in holder_names]

            if period:
                edge_rows = conn.execute(f"""
                    SELECT shareholder_name, stock_code, share_percent
                    FROM shareholders
                    WHERE UPPER(shareholder_name) IN ({placeholders})
                      AND data_period = ? AND share_percent >= 0.5
                    ORDER BY share_percent DESC
                """, (*name_upper, period))
            else:
                edge_rows = conn.execute(f"""
                    SELECT shareholder_name, stock_code, share_percent
                    FROM shareholders
                    WHERE UPPER(shareholder_name) IN ({placeholders})
                      AND share_percent >= 0.5
                    ORDER BY share_percent DESC
                """, (*name_upper,))

            edges_raw = [dict(r) for r in edge_rows]

        stock_set = set()
        nodes = []
        edges = []
        node_ids = set()

        for h in top_holders:
            nid = "sh:" + h["shareholder_name"]
            nodes.append({
                "id": nid, "label": h["shareholder_name"][:30],
                "type": "shareholder", "value": h["total_pct"],
                "size": min(50, max(15, round(h["total_pct"] / 10))),
                "stock_count": h["stock_count"],
                "total_pct": h["total_pct"]
            })
            node_ids.add(nid)

        for e in edges_raw:
            sid = "st:" + e["stock_code"]
            if sid not in node_ids:
                nodes.append({
                    "id": sid, "label": e["stock_code"],
                    "type": "stock", "value": 10, "size": 10
                })
                node_ids.add(sid)
                stock_set.add(e["stock_code"])
            edges.append({
                "from": "sh:" + e["shareholder_name"],
                "to": sid,
                "value": max(1, e["share_percent"]),
                "title": f"{e['share_percent']}%"
            })

        return {
            "status": "ok", "nodes": nodes, "edges": edges,
            "meta": {
                "holders": len(top_holders),
                "stocks": len(stock_set),
                "connections": len(edges_raw)
            }
        }
    except Exception as e:
        logger.error("force-graph error: %s", e)
        return {"status": "error", "nodes": [], "edges": [], "error": str(e)}

@router.get("/shareholders/network-data")
def shareholder_network_data(period: Optional[str] = None, limit: int = 40):
    """Force-directed graph data: top shareholders connected to stocks they hold."""
    try:
        from app.services.shareholder_service import get_db
        from app.services.stock_service import STOCK_LIST
        with get_db() as conn:
            # 1. Get top shareholders
            if period:
                rows = conn.execute("""
                    SELECT shareholder_name, COUNT(*) as stock_count,
                           ROUND(SUM(share_percent), 2) as total_pct
                    FROM shareholders
                    WHERE data_period = ? AND share_percent >= 0.5
                    GROUP BY shareholder_name
                    HAVING total_pct >= 1
                    ORDER BY total_pct DESC
                    LIMIT ?
                """, (period, limit))
            else:
                rows = conn.execute("""
                    SELECT shareholder_name, COUNT(*) as stock_count,
                           ROUND(SUM(share_percent), 2) as total_pct
                    FROM shareholders
                    WHERE share_percent >= 0.5
                    GROUP BY shareholder_name
                    HAVING total_pct >= 1
                    ORDER BY total_pct DESC
                    LIMIT ?
                """, (limit,))
            top_holders = [dict(r) for r in rows]
            holder_names = [h["shareholder_name"] for h in top_holders]

            if not holder_names:
                return {"status": "ok", "nodes": [], "edges": []}

            # 2. Get their stock holdings (edges)
            placeholders = ",".join("?" * len(holder_names))
            if period:
                rows2 = conn.execute(f"""
                    SELECT s.stock_code, s.shareholder_name,
                           ROUND(s.share_percent, 2) as share_percent
                    FROM shareholders s
                    WHERE s.shareholder_name IN ({placeholders})
                    AND s.data_period = ? AND s.share_percent >= 0.5
                    ORDER BY s.share_percent DESC
                """, holder_names + [period])
            else:
                rows2 = conn.execute(f"""
                    SELECT s.stock_code, s.shareholder_name,
                           ROUND(s.share_percent, 2) as share_percent
                    FROM shareholders s
                    WHERE s.shareholder_name IN ({placeholders})
                    AND s.share_percent >= 0.5
                    ORDER BY s.share_percent DESC
                """, holder_names)
            edges_raw = [dict(r) for r in rows2]

            # 3. Build nodes + edges
            stock_codes = set()
            edges = []
            seen_edges = set()
            for e in edges_raw:
                key = f"{e['shareholder_name']}|{e['stock_code']}"
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                stock_codes.add(e["stock_code"])
                edges.append({
                    "from": f"sh:{e['shareholder_name']}",
                    "to": f"st:{e['stock_code']}",
                    "value": max(0.5, e["share_percent"]),
                    "title": f"{e['share_percent']}%"
                })

            # 4. Build nodes
            nodes = []
            seen_sh = set()
            for h in top_holders:
                nid = f"sh:{h['shareholder_name']}"
                if nid in seen_sh:
                    continue
                seen_sh.add(nid)
                sh_label = h["shareholder_name"]
                if len(sh_label) > 30:
                    sh_label = sh_label[:28] + "..."
                nodes.append({
                    "id": nid,
                    "label": sh_label,
                    "title": h["shareholder_name"],
                    "type": "shareholder",
                    "value": h["total_pct"],
                    "color": "#EF4444",
                    "shape": "dot",
                    "size": min(50, 10 + h["total_pct"] / 10),
                    "group": "shareholder"
                })

            seen_st = set()
            for sc in sorted(stock_codes):
                nid = f"st:{sc}"
                if nid in seen_st:
                    continue
                seen_st.add(nid)
                stock_name = STOCK_LIST.get(sc, "")
                label = sc
                if stock_name:
                    sn = stock_name[:25]
                    if len(stock_name) > 25:
                        sn += "..."
                    label = f"{sc} ({sn})"
                nodes.append({
                    "id": nid,
                    "label": label,
                    "title": f"{sc} - {stock_name}" if stock_name else sc,
                    "type": "stock",
                    "value": 1,
                    "color": "#3B82F6",
                    "shape": "square",
                    "size": 15,
                    "group": "stock"
                })

            return {"status": "ok", "nodes": nodes, "edges": edges}
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


@router.get("/shareholders/distribution")
def shareholder_distribution(period: str = Query(...)):
    """Distribution of holdings by category (for donut chart)."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            cur = conn.execute("""
                SELECT
                    SUM(CASE WHEN share_percent >= 5 THEN 1 ELSE 0 END) as large,
                    SUM(CASE WHEN share_percent >= 1 AND share_percent < 5 THEN 1 ELSE 0 END) as medium,
                    SUM(CASE WHEN share_percent >= 0.5 AND share_percent < 1 THEN 1 ELSE 0 END) as small,
                    SUM(CASE WHEN share_percent < 0.5 THEN 1 ELSE 0 END) as tiny,
                    COUNT(*) as total
                FROM shareholders WHERE data_period = ?
            """, (period,))
            row = dict(cur.fetchone())
        return {
            "status": "ok", "period": period, "distribution": row,
            "labels": {
                "large": "\u22655% (Pengendali)", "medium": "1-5% (Signifikan)",
                "small": "0.5-1% (Minoritas)", "tiny": "<0.5% (Pemodal Kecil)"
            }
        }
    except Exception as e:
        logger.error("distribution error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/shareholders/top-stocks")
def shareholder_top_stocks(
    period: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
):
    """Stocks with most shareholders (for bar chart)."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            rows = conn.execute("""
                SELECT stock_code, COUNT(*) as holder_count,
                       ROUND(SUM(share_percent), 2) as total_pct,
                       ROUND(AVG(share_percent), 2) as avg_pct
                FROM shareholders WHERE data_period = ?
                GROUP BY stock_code
                ORDER BY holder_count DESC
                LIMIT ?
            """, (period, limit))
            data = [dict(r) for r in rows]
        return {"status": "ok", "period": period, "data": data}
    except Exception as e:
        logger.error("top-stocks error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/shareholders/stats/detail")
def shareholder_stats_detail(period: str = Query(...)):
    """Detailed aggregate stats for a period."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            stocks = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            holders = conn.execute("SELECT COUNT(DISTINCT shareholder_name) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            top = conn.execute("""
                SELECT shareholder_name, COUNT(*) as stock_count, ROUND(SUM(share_percent), 2) as total_pct
                FROM shareholders WHERE data_period=?
                GROUP BY shareholder_name ORDER BY total_pct DESC LIMIT 1
            """, (period,)).fetchone()
            mhs = conn.execute("""
                SELECT stock_code, COUNT(*) as cnt FROM shareholders
                WHERE data_period=? GROUP BY stock_code ORDER BY cnt DESC LIMIT 1
            """, (period,)).fetchone()
            avg_pct = conn.execute(
                "SELECT ROUND(AVG(share_percent), 2) FROM shareholders WHERE data_period=?", (period,)
            ).fetchone()[0] or 0
        avg_holders = round(stocks / holders, 1) if holders else 0
        return {
            "status": "ok", "period": period,
            "stats": {
                "total_records": total, "total_stocks": stocks, "total_holders": holders,
                "top_holder": top[0] if top else "-",
                "top_holder_stocks": top[1] if top else 0,
                "top_holder_pct": top[2] if top else 0,
                "most_held_stock": mhs[0] if mhs else "-",
                "most_held_count": mhs[1] if mhs else 0,
                "avg_holders_per_stock": avg_holders,
                "avg_pct_per_holder": avg_pct,
            }
        }
    except Exception as e:
        logger.error("stats/detail error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/shareholders/concentration")
def shareholder_concentration(
    period: str = Query(...),
    threshold: float = Query(5.0, ge=0.1, le=100),
):
    """Stock concentration - stocks with dominant holders."""
    try:
        from app.services.shareholder_service import get_db
        # Data fix
        period = period.strip().upper()
        if period == '2026-02': period = 'FEB2026'

        with get_db() as conn:
            rows = conn.execute("""
                SELECT stock_code, ROUND(MAX(share_percent), 2) as top_holder_pct,
                       ROUND(SUM(share_percent), 2) as total_owned_pct,
                       COUNT(*) as holder_count
                FROM shareholders WHERE data_period=?
                GROUP BY stock_code
                HAVING top_holder_pct >= ?
                ORDER BY top_holder_pct DESC LIMIT 10
            """, (period, threshold))

            total_stocks = conn.execute(
                "SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE data_period=?", (period,)
            ).fetchone()[0]
            rows = list(rows)
        return {
            "status": "ok", "period": period,
            "dominant_stocks": rows,
            "summary": {
                "total_dominant": len(rows),
                "dominant_pct": round(len(rows) / total_stocks * 100, 1) if total_stocks else 0
            }
        }
    except Exception as e:
        logger.error("concentration error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/shareholders/scatter-data")
def shareholder_scatter(period: str = Query("FEB2026")):
    """All stocks' shareholder aggregation for scatter plot."""
    from app.services.shareholder_service import get_db
    try:
        period = period.strip().upper()
        if period == '2026-02': period = 'FEB2026'
        with get_db() as conn:
            rows = conn.execute("""
                SELECT stock_code,
                       ROUND(MAX(share_percent), 2) as top_pct,
                       ROUND(SUM(share_percent), 2) as total_pct,
                       COUNT(*) as holders
                FROM shareholders WHERE data_period=?
                GROUP BY stock_code
                ORDER BY stock_code
            """, (period,))
            data = list(rows)
        return {"status": "ok", "period": period, "total": len(data), "data": data}
    except Exception as e:
        logger.error("scatter error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/shareholders/insight")
async def shareholders_insight():
    """AI-generated insight from shareholder data."""
    from openai import OpenAI
    from app.database.database import get_db

    period = 'FEB2026'
    data = {}

    try:
        with get_db() as conn:
            total_records = conn.execute("SELECT COUNT(*) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            total_stocks = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            total_holders = conn.execute("SELECT COUNT(DISTINCT shareholder_name) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]

            top_holders = conn.execute("""
                SELECT shareholder_name, COUNT(DISTINCT stock_code) as stock_count,
                       ROUND(SUM(share_percent), 2) as total_pct
                FROM shareholders WHERE data_period=?
                GROUP BY shareholder_name ORDER BY stock_count DESC LIMIT 10
            """, (period,)).fetchall()

            top_stocks = conn.execute("""
                SELECT stock_code, COUNT(*) as holder_count,
                       ROUND(SUM(share_percent), 2) as total_pct
                FROM shareholders WHERE data_period=?
                GROUP BY stock_code ORDER BY holder_count DESC LIMIT 10
            """, (period,)).fetchall()

            high_conc = conn.execute("""
                SELECT COUNT(DISTINCT a.stock_code) 
                FROM shareholders a
                JOIN (
                    SELECT stock_code, MAX(share_percent) as max_pct 
                    FROM shareholders WHERE data_period=? GROUP BY stock_code
                ) as top_holders ON a.stock_code = top_holders.stock_code AND a.share_percent = top_holders.max_pct
                WHERE a.data_period=?
            """, (period, period)).fetchone()[0]

            spread = conn.execute("""
                SELECT CASE WHEN cnt=1 THEN '1'
                    WHEN cnt<=5 THEN '2-5'
                    WHEN cnt<=10 THEN '6-10'
                    WHEN cnt<=20 THEN '11-20'
                    ELSE '>20' END as bucket,
                    COUNT(*) as count FROM (
                    SELECT stock_code, COUNT(*) as cnt
                    FROM shareholders WHERE data_period=?
                    GROUP BY stock_code
                ) GROUP BY bucket ORDER BY bucket
            """, (period,)).fetchall()

            data = {
                "total_records": total_records,
                "total_stocks": total_stocks,
                "total_holders": total_holders,
                "avg_holders_per_stock": round(total_records / max(total_stocks, 1), 1),
                "top_holders": [{"name": r[0], "stocks": r[1], "pct": r[2]} for r in top_holders],
                "top_stocks": [{"code": r[0], "holders": r[1], "total_pct": r[2]} for r in top_stocks],
                "high_concentration_stocks": high_conc,
                "holder_distribution": {r[0]: r[1] for r in spread},
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    prompt = f"""Analyze this shareholder ownership data for the Indonesian stock market (period: {period}) and provide investment insights in BAHASA INDONESIA.

DATA:
- Total records: {data['total_records']}
- Total stocks tracked: {data['total_stocks']}
- Total unique shareholders: {data['total_holders']}
- Average holders per stock: {data['avg_holders_per_stock']}
- Stocks with dominant holder (>50%): {data['high_concentration_stocks']} ({round(data['high_concentration_stocks']/max(data['total_stocks'],1)*100)}%)

Top 10 Shareholders (by number of stocks held):
{chr(10).join(f"  {h['name']}: {h['stocks']} stocks, {h['pct']}% total" for h in data['top_holders'])}

Top 10 Most-Held Stocks:
{chr(10).join(f"  {s['code']}: {s['holders']} holders, {s['total_pct']}% total" for s in data['top_stocks'])}

Holder Distribution (how many stocks have X holders):
{chr(10).join(f"  {k} holders: {v} stocks" for k,v in data['holder_distribution'].items())}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "narrative": "2-3 paragraph analysis in BAHASA INDONESIA describing landscape, concentration risks, market structure",
  "key_findings": ["3-5 bullet poin penting dalam BAHASA INDONESIA"],
  "risks": ["2-4 risiko investasi terkait konsentrasi kepemilikan, in BAHASA INDONESIA"],
  "opportunities": ["2-3 peluang atau sinyal positif, in BAHASA INDONESIA"],
  "recommendations": ["2-4 rekomendasi actionable untuk investor, in BAHASA INDONESIA"]
}}"""

    try:
        client = OpenAI(api_key=Config.NINE_ROUTER_API_KEY, base_url=Config.NINE_ROUTER_BASE_URL, timeout=30)
        resp = client.chat.completions.create(
            model=Config.NINE_ROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are an Indonesian stock market analyst. Analyze shareholder data and return ONLY valid JSON in BAHASA INDONESIA. When generating SQL, ensure all derived tables in SQL subqueries have explicit aliases (e.g., `(SELECT ... FROM table) AS alias_name`)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content or ""
        reasoning = getattr(resp.choices[0].message, "reasoning_content", None) or ""
        if not raw.strip() and reasoning.strip():
            raw = reasoning
        import re
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        parsed = json.loads(raw)
        return {"status": "ok", "insight": parsed, "data": data}
    except json.JSONDecodeError:
        return {"status": "ok", "insight": {"narrative": raw[:1500], "key_findings": ["AI returned unstructured response"], "risks": [], "opportunities": [], "recommendations": []}, "data": data}
    except Exception as e:
        top_holder = data['top_holders'][0]['name'] if data['top_holders'] else 'N/A'
        return {
            "status": "ok",
            "insight": {
                "narrative": f"Overview {period}: {data['total_stocks']} saham dipantau dengan {data['total_holders']} pemegang saham unik. Top holder {top_holder} memegang {data['top_holders'][0]['stocks'] if data['top_holders'] else 0} saham. {data['high_concentration_stocks']} saham ({round(data['high_concentration_stocks']/max(data['total_stocks'],1)*100)}%) didominasi satu pemegang >50% - indikasi risiko konsentrasi.",
                "key_findings": [
                    f"{data['total_holders']} pemegang saham unik di {data['total_stocks']} saham",
                    f"{top_holder} portofolio terluas: {data['top_holders'][0]['stocks'] if data['top_holders'] else 0} saham",
                    f"{data['high_concentration_stocks']} saham ({round(data['high_concentration_stocks']/max(data['total_stocks'],1)*100)}%) dikuasai 1 pemegang >50%",
                    f"Rata-rata {data['avg_holders_per_stock']} pemegang/saham - {'cukup tersebar' if data['avg_holders_per_stock'] > 5 else 'likuiditas rendah'}",
                ],
                "risks": [f"Konsentrasi tinggi: {data['high_concentration_stocks']} saham dikuasai 1 pemegang"],
                "opportunities": ["Base holder diversified di saham top menjanjikan stabilitas"],
                "recommendations": ["Fokus saham dengan distribusi holder merata untuk likuiditas lebih baik"],
            },
            "data": data,
            "source": "template_fallback"
        }


@router.get("/shareholders/{stock_code}")
def shareholder_by_stock(stock_code: str, period: Optional[str] = None):
    """Get shareholder >1% data for a stock."""
    return {
        "status": "ok",
        "stock_code": stock_code.upper(),
        "period": period or "latest",
        "data": get_shareholders_by_stock(stock_code, period),
    }


class ShareholderImportItem(BaseModel):
    stock_code: str
    shareholder_name: str
    share_percent: float
    share_count: int = 0
    category: str = ''


class ShareholderImportRequest(BaseModel):
    period: str
    data: List[ShareholderImportItem]
    source: str = 'manual'


@router.post("/shareholders/import")
def shareholder_import(req: ShareholderImportRequest):
    """Import shareholder data (single or batch)."""
    items = [item.model_dump() for item in req.data]
    result = bulk_import(items, req.period)
    return {"status": "ok", "period": req.period, **result}


@router.get("/shareholders/trends")
def shareholder_trends(period: str = Query(...), prev_period: str = Query(...)):
    """Get month-over-month trends for top shareholders."""
    from app.services.shareholder_service import get_shareholder_trends
    trends = get_shareholder_trends(period, prev_period)
    return {"status": "ok", "period": period, "prev_period": prev_period, "trends": trends}


def _detect_period_from_pdf(filename: str, content: bytes = None) -> str | None:
    """Detect period (e.g. JUN2026) from PDF filename or content."""
    import re
    months_map = {'01':'JAN','02':'FEB','03':'MAR','04':'APR','05':'MAY','06':'JUN',
                  '07':'JUL','08':'AUG','09':'SEP','10':'OCT','11':'NOV','12':'DEC'}
    valid_months = set(months_map.values())

    # Indonesian → EN month mapping
    id_en = {
        'JANUARI':'JAN','FEBRUARI':'FEB','MARET':'MAR','APRIL':'APR','MEI':'MAY','JUNI':'JUN',
        'JULI':'JUL','AGUSTUS':'AUG','SEPTEMBER':'SEP','OKTOBER':'OCT','NOVEMBER':'NOV','DESEMBER':'DEC'
    }
    # English 3-letter → uppercase month
    en_3 = {'JAN':'JAN','FEB':'FEB','MAR':'MAR','APR':'APR','MAY':'MAY','JUN':'JUN',
            'JUL':'JUL','AUG':'AUG','SEP':'SEP','OCT':'OCT','NOV':'NOV','DEC':'DEC'}

    candidates = []

    # 1) Try filename patterns
    if filename:
        base = filename.rsplit('.', 1)[0].strip().upper()
        m = re.search(r'([A-Z]{3})(\d{4})', base)
        if m and m.group(1) in valid_months:
            candidates.append(m.group(1) + m.group(2))
        m = re.search(r'(0[1-9]|1[012])(\d{4})', base)
        if m:
            candidates.append(months_map.get(m.group(1), '') + m.group(2))
        m = re.search(r'(\d{4})(0[1-9]|1[012])', base)
        if m:
            candidates.append(months_map.get(m.group(2), '') + m.group(1))

    # 2) Try PDF content (first page text)
    if not candidates and content:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc[:3]:  # first 3 pages
                text = page.get_text() or ''
                text_upper = text.upper()
                # Pattern: month name + year (e.g. JUNI 2026)
                for id_month, en_month in id_en.items():
                    pat = rf'{id_month}\s*(\d{{4}})'
                    m = re.search(pat, text_upper)
                    if m:
                        candidates.append(en_month + m.group(1))
                # Pattern: Periode: 06/2026
                m = re.search(r'PERIODE[:\s]*(\d{2})[/\s]*(\d{4})', text_upper)
                if m:
                    candidates.append(months_map.get(m.group(1).zfill(2), '') + m.group(2))
                # Pattern: Periode: JUN 2026 / JUNI2026
                m = re.search(r'PERIODE[:\s]*([A-Z]{3,})[\s/]*(\d{4})', text_upper)
                if m:
                    mon = m.group(1)[:3]
                    if mon in valid_months:
                        candidates.append(mon + m.group(2))
                    elif m.group(1) in id_en:
                        candidates.append(id_en[m.group(1)] + m.group(2))
                # Pattern: DD Month YYYY (e.g. "30 Juni 2026")
                for id_month, en_month in id_en.items():
                    pat = rf'\d{{1,2}}\s+{id_month}\s+(\d{{4}})'
                    m = re.search(pat, text_upper)
                    if m:
                        candidates.append(en_month + m.group(1))
                # Pattern: DD-Mon-YYYY (e.g. "31-Mar-2026") — C-BEST, often no space after year
                m = re.search(r'\b(\d{2})-([A-Z]{3})-(\d{4})', text_upper)
                if m:
                    mon = m.group(2).capitalize()
                    mon3 = mon[:3].upper()
                    if mon3 in en_3:
                        candidates.append(en_3[mon3] + m.group(3))
                if candidates:
                    break
            doc.close()
        except Exception:
            pass

    return candidates[0] if candidates else None


def _parse_pdf_table(content: bytes) -> list:
    """Parse PDF table data using fitz (thread-safe, no blocking)."""
    import fitz, re
    doc = fitz.open(stream=content, filetype="pdf")
    rows, seen = [], set()
    max_pages = min(len(doc), 10)
    for page in doc[:max_pages]:
        for table in page.find_tables():
            tbl = table.extract()
            if not tbl or len(tbl) < 2:
                continue
            header = [str(h).strip().lower() if h else '' for h in tbl[0]]

            def _find_col(needles):
                for n in needles:
                    for i, h in enumerate(header):
                        if n in h:
                            return i
                return None

            ci_code = _find_col(['kode', 'code', 'stock', 'saham', 'emiten'])
            ci_name = _find_col(['investor', 'pemegang', 'shareholder', 'nama', 'name'])
            ci_pct = _find_col(['%', 'persen', 'percent', 'pct', '%saham', 'saham%'])
            ci_cnt = _find_col(['total', 'jumlah', 'amount', 'count', 'shares', 'lembar', 'qty'])
            if ci_code is None and ci_name is None:
                continue
            for row in tbl[1:]:
                if not row or len(row) <= max(ci_code or 0, ci_name or 0):
                    continue
                try:
                    sc = re.sub(r'[^A-Z0-9]', '', (str(row[ci_code] or '')).upper()) if ci_code is not None else ''
                    nm = re.sub(r'\s+', ' ', (str(row[ci_name] or '')).strip().upper()) if ci_name is not None else ''
                    pct = 0.0
                    cnt = 0
                    if ci_pct is not None:
                        val = str(row[ci_pct] or '0').strip().replace(',', '.').replace('%', '')
                        m = re.search(r'[\d.]+', val)
                        if m: pct = float(m.group())
                    if ci_cnt is not None:
                        val = str(row[ci_cnt] or '0').strip().replace(',', '')
                        m = re.search(r'[\d]+', val)
                        if m: cnt = int(m.group())
                except (ValueError, IndexError):
                    continue
                if not sc or not nm or pct <= 0:
                    continue
                dedup = f'{sc}|{nm}|{pct:.4f}'
                if dedup in seen:
                    continue
                seen.add(dedup)
                rows.append(dict(stock_code=sc, shareholder_name=nm, share_percent=round(pct, 2), share_count=cnt))
    doc.close()
    return rows


@router.post("/shareholders/upload")
async def shareholder_upload(
    file: UploadFile = File(...),
    period: str = Form(""),
):
    """Upload CSV or Excel file to import shareholder data."""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('csv', 'xlsx', 'pdf'):
        raise HTTPException(400, "Only .csv, .xlsx, or .pdf files accepted")

    period = period.strip().upper()

    import io
    content = await file.read()

    # Auto-detect period for PDF if not provided
    if not period and ext == 'pdf':
        detected = _detect_period_from_pdf(file.filename, content)
        if detected:
            period = detected
        else:
            raise HTTPException(400, "Tidak bisa mendeteksi periode dari file. Mohon masukkan periode manual (contoh: JUN2026)")

    if not period:
        raise HTTPException(400, "Period is required (e.g. JUN2026)")

    import csv

    rows = []
    try:
        if ext == 'csv':
            text = content.decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                sc = row.get('stock_code', '').strip().upper()
                nm = row.get('shareholder_name', '').strip().upper()
                pct_str = row.get('share_percent', '0').strip().replace(',', '.')
                cnt_str = row.get('share_count', '0').strip()
                try:
                    pct = float(pct_str) if pct_str else 0
                    cnt = int(cnt_str) if cnt_str else 0
                except ValueError:
                    continue
                if not sc or not nm or pct <= 0:
                    continue
                rows.append({
                    'stock_code': sc,
                    'shareholder_name': nm,
                    'share_percent': pct,
                    'share_count': cnt,
                })
        elif ext == 'xlsx':
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content), dtype=str)
            df.columns = [c.strip().lower() for c in df.columns]
            for _, row in df.iterrows():
                sc = str(row.get('stock_code', '')).strip().upper()
                nm = str(row.get('shareholder_name', '')).strip().upper()
                pct_str = str(row.get('share_percent', '0')).strip().replace(',', '.')
                cnt_str = str(row.get('share_count', '0')).strip()
                try:
                    pct = float(pct_str) if pct_str else 0
                    cnt = int(float(cnt_str)) if cnt_str else 0
                except ValueError:
                    continue
                if not sc or not nm or pct <= 0:
                    continue
                rows.append({
                    'stock_code': sc,
                    'shareholder_name': nm,
                    'share_percent': pct,
                    'share_count': cnt,
                })
        elif ext == 'pdf':
            import asyncio
            loop = asyncio.get_running_loop()
            rows = await loop.run_in_executor(None, _parse_pdf_table, content)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {e}")

    if not rows:
        raise HTTPException(400, "No valid data found in file")

    # Warn if this period already has data
    exists = period_has_data(period)

    result = bulk_import(rows, period)
    return {"status": "ok", "period": period, "exists": exists, **result}


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


@router.get("/day-trade/candidates")
async def day_trade_candidates():
    try:
        from app.ai.strategies.bpjs_strategy import BPJSStrategy
        candidates = BPJSStrategy().scan_candidates()
        return {
            "status": "ok",
            "data": {
                "candidates": candidates,
                "count": len(candidates),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
    except Exception as e:
        logger.warning("Day trade candidates error: %s", e)
        return {
            "status": "ok",
            "data": {
                "candidates": [],
                "count": 0,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e),
            },
        }


@router.get("/day-trade/{code}")
async def day_trade_analysis(code: str):
    from app.ai.strategies.bpjs_strategy import BPJSStrategy
    result = BPJSStrategy().analyze(code)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"status": "ok", "data": result}


@router.get("/scored-analysis/{code}")
async def get_scored_analysis(
    code: str,
    strategy: str = Query("swing", description="Strategy: swing, day_trade, long_term"),
    risk_level: str = Query("moderate", description="Risk level: low, moderate, high"),
):
    engine = ScoringEngine()
    try:
        result = engine.calculate_score(code, strategy, risk_level)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "status": "ok",
        "data": {
            "stock_code": result.stock_code,
            "strategy": result.strategy,
            "risk_level": result.risk_level,
            "total_score": result.total_score,
            "recommendation": result.recommendation,
            "confidence": result.confidence,
            "summary": result.summary,
            "risks": result.risks,
            "catalysts": result.catalysts,
            "components": [asdict(c) for c in result.components],
            "last_updated": result.last_updated,
        },
    }


@router.get("/long-term/{code}")
async def long_term_analysis(code: str):
    from app.ai.strategies.creative_trader_strategy import CreativeTraderStrategy
    strategy = CreativeTraderStrategy()
    data = strategy.analyze(code)
    return {"status": "ok", "data": data}


@router.get("/long-term/candidates")
async def long_term_candidates():
    try:
        from app.ai.strategies.creative_trader_strategy import CreativeTraderStrategy
        strategy = CreativeTraderStrategy()
        candidates = strategy.scan_for_long_term_candidates()
        return {
            "status": "ok",
            "data": {
                "candidates": candidates,
                "count": len(candidates),
                "last_updated": datetime.now().isoformat(),
            },
        }
    except Exception as e:
        logger.warning("Long-term candidates error: %s", e)
        return {
            "status": "ok",
            "data": {
                "candidates": [],
                "count": 0,
                "last_updated": datetime.now().isoformat(),
                "error": str(e),
            },
        }


@router.get("/market-reports")
async def get_market_reports(limit: int = Query(500, description="Max reports to return", le=1000)):
    """Get parsed market reports from @creativetrader."""
    from app.database.database import get_market_reports
    reports = get_market_reports(limit)
    if not reports:
        return {"status": "ok", "data": [], "message": "No reports yet. Run market_report_scraper.py first."}
    return {"status": "ok", "data": reports, "total": len(reports)}


@router.get("/market-report-analysis")
async def get_market_report_analysis():
    """AI analysis + backtest of market reports from @creativetrader."""
    from collections import Counter, defaultdict
    from datetime import datetime
    from app.database.database import get_market_reports

    reports = get_market_reports(1000)
    if not reports:
        return {"status": "ok", "analysis": None, "message": "No reports yet."}

    # -- Basic Stats --
    dates = sorted(set(r["date"] for r in reports))
    ihsg_vals = [r["ihsg_change"] for r in reports if r["ihsg_change"] is not None]
    avg_ihsg = round(sum(ihsg_vals) / len(ihsg_vals), 1) if ihsg_vals else 0
    red_days = sum(1 for v in ihsg_vals if v < 0)
    green_days = sum(1 for v in ihsg_vals if v > 0)

    # -- Foreign Buy Aggregation --
    foreign_total = defaultdict(float)
    foreign_freq = Counter()
    foreign_by_month = defaultdict(lambda: defaultdict(float))

    for r in reports:
        m = r["date"][:7]
        for fb in r.get("foreign_buy", []):
            foreign_total[fb["stock"]] += fb["value"]
            foreign_freq[fb["stock"]] += 1
            foreign_by_month[m][fb["stock"]] += fb["value"]

    top_foreign = [
        {"stock": s, "total": round(v, 2), "freq": foreign_freq[s]}
        for s, v in sorted(foreign_total.items(), key=lambda x: -x[1])[:15]
    ]

    monthly_flow = []
    for m in sorted(foreign_by_month.keys()):
        total_t = sum(foreign_by_month[m].values())
        top5 = sorted(foreign_by_month[m].items(), key=lambda x: -x[1])[:5]
        rpt_count = sum(1 for r in reports if r["date"].startswith(m))
        monthly_flow.append({
            "month": m, "total": round(total_t, 2),
            "reports": rpt_count,
            "top": [{"stock": s, "value": round(v, 2)} for s, v in top5]
        })

    # -- IHSG Trend --
    periods = [
        {"label": "Mei-Jun 2026", "start": "2026-05-01", "end": "2026-06-30"},
        {"label": "April 2026", "start": "2026-04-01", "end": "2026-04-30"},
        {"label": "Maret 2026", "start": "2026-03-01", "end": "2026-03-31"},
    ]
    ihsg_trend = []
    for p in periods:
        vals = [r["ihsg_change"] for r in reports if p["start"] <= r["date"] <= p["end"] and r["ihsg_change"] is not None]
        if vals:
            avg = sum(vals) / len(vals)
            ihsg_trend.append({
                "label": p["label"],
                "avg": round(avg, 1),
                "red": sum(1 for v in vals if v < 0),
                "total": len(vals)
            })

    # -- Backtest --
    by_date = defaultdict(list)
    for r in reports:
        by_date[r["date"]].append(r)
    sorted_dates = sorted(by_date.keys())

    # V1: Foreign buy -> gainer in 3 days
    win_v1 = 0
    loss_v1 = 0
    best_stocks = Counter()
    best_total = Counter()
    same_day_signal = Counter()

    for i, d in enumerate(sorted_dates):
        day_reports = by_date[d]
        full = next((r for r in day_reports if r["type"] == "full"), day_reports[0])
        foreign = full.get("foreign_buy", [])
        if not foreign:
            continue
        future_dates = sorted_dates[i+1:i+4]
        if len(future_dates) < 2:
            continue
        future_gainers = set()
        future_losers = set()
        for fd in future_dates:
            for fr in by_date[fd]:
                for g in fr.get("gainers", []):
                    future_gainers.add(g["stock"])
                for g in fr.get("losers", []):
                    future_losers.add(g["stock"])
        for f in foreign[:3]:
            s = f["stock"]
            best_total[s] += 1
            if s in future_gainers:
                win_v1 += 1
                best_stocks[s] += 1
            else:
                loss_v1 += 1

    # Same-day signal: foreign buy + gainer same day
    for d in sorted_dates:
        for r in by_date[d]:
            fb_stocks = set(f["stock"] for f in r.get("foreign_buy", []))
            gainer_stocks = set(g["stock"] for g in r.get("gainers", []))
            for s in fb_stocks & gainer_stocks:
                same_day_signal[s] += 1

    # V2: Sesi1 gainer -> sesi2 gainer (intraday)
    win_v2 = 0
    loss_v2 = 0
    for d in sorted_dates:
        dr = by_date[d]
        s1 = next((r for r in dr if r["type"] == "session1"), None)
        full = next((r for r in dr if r["type"] == "full"), None)
        if not s1 or not full:
            continue
        s1_gainers = set(s["stock"] for s in s1.get("gainers", []))
        eod_gainers = set(s["stock"] for s in full.get("gainers", []))
        eod_losers = set(s["stock"] for s in full.get("losers", []))
        for stock in s1_gainers:
            if stock in eod_gainers:
                win_v2 += 1
            else:
                loss_v2 += 1

    # V3: Weekly consistency
    weeks = defaultdict(list)
    for r in reports:
        d_obj = datetime.strptime(r["date"], "%Y-%m-%d")
        wk = d_obj.strftime("%Y-W%W")
        weeks[wk].append(r)
    week_list = sorted(weeks.keys())
    cons_win = cons_loss = 0
    for i, wk in enumerate(week_list[:-1]):
        next_wk = week_list[i+1]
        next_gainers = set()
        fb_this = Counter()
        for r in weeks[wk]:
            for fb in r.get("foreign_buy", []):
                fb_this[fb["stock"]] += 1
        for r in weeks[next_wk]:
            for g in r.get("gainers", []):
                next_gainers.add(g["stock"])
        for stock, count in fb_this.items():
            if count >= 2:
                if stock in next_gainers:
                    cons_win += 1
                else:
                    cons_loss += 1

    # Best picks
    top_picks = []
    for s in best_stocks:
        t = best_total[s]
        top_picks.append({"stock": s, "wins": best_stocks[s], "total": t})
    top_picks.sort(key=lambda x: -x["wins"])

    same_day_list = [{"stock": s, "count": c} for s, c in same_day_signal.most_common(8)]

    # -- Recent Foreign Buy (last 7 days) --
    last_week = [d for d in sorted_dates if d >= "2026-06-01"]
    recent_foreign_raw = defaultdict(float)
    recent_freq = Counter()
    for d in last_week:
        for r in by_date[d]:
            for fb in r.get("foreign_buy", []):
                recent_foreign_raw[fb["stock"]] += fb["value"]
                recent_freq[fb["stock"]] += 1
    recent_hot = [
        {"stock": s, "total": round(v, 2), "freq": recent_freq[s],
         "same_day": same_day_signal.get(s, 0)}
        for s, v in sorted(recent_foreign_raw.items(), key=lambda x: -x[1])[:8]
    ]

    # -- IHSG Outlook --
    latest5 = ihsg_vals[:5]
    latest_avg = round(sum(latest5) / len(latest5), 1) if latest5 else 0
    if latest_avg < -2:
        outlook = "bearish"
    elif latest_avg < 0:
        outlook = "koreksi"
    else:
        outlook = "stabil"

    return {
        "status": "ok",
        "analysis": {
            "period": {"start": dates[0], "end": dates[-1], "days": len(dates), "total_reports": len(reports)},
            "ihsg_summary": {"avg": avg_ihsg, "red_days": red_days, "green_days": green_days, "total": len(ihsg_vals)},
            "top_foreign": top_foreign,
            "monthly_flow": monthly_flow,
            "ihsg_trend": ihsg_trend,
            "backtest": {
                "v1": {"label": "Beli Top 3 Foreign Buy -> Gainer 3 hari", "trades": win_v1 + loss_v1, "wins": win_v1, "losses": loss_v1, "win_rate": round(win_v1 / max(win_v1 + loss_v1, 1) * 100)},
                "v2": {"label": "Beli Top Gainer Sesi1 -> jual akhir sesi", "trades": win_v2 + loss_v2, "wins": win_v2, "losses": loss_v2, "win_rate": round(win_v2 / max(win_v2 + loss_v2, 1) * 100)},
                "v3": {"label": "Saham >=2 foreign buy/minggu -> gainer minggu depan", "trades": cons_win + cons_loss, "wins": cons_win, "losses": cons_loss, "win_rate": round(cons_win / max(cons_win + cons_loss, 1) * 100)},
            },
            "same_day_signals": same_day_list,
            "top_picks": top_picks[:5],
            "recent_hot": recent_hot,
            "ihsg_outlook": {
                "latest": [round(v, 1) for v in latest5],
                "avg": latest_avg,
                "status": outlook,
            }
        }
    }

@router.get("/treemap")
def treemap_data():
    """Market heatmap treemap - stocks grouped by sector."""
    return get_treemap_data()


@router.get("/market-backtest")
def market_backtest():
    """Backtest: beli saham yg naik di Sesi 1 -> tahan sampai akhir sesi."""
    from app.database.database import get_market_reports
    from collections import defaultdict

    reports = get_market_reports(limit=1000)
    by_date = defaultdict(list)
    for r in reports:
        by_date[r['date']].append(r)

    paired_dates = {k: v for k, v in by_date.items()
                    if any(x['type']=='sesi1' for x in v) and any(x['type']=='akhir_sesi' for x in v)}

    total_s1_gainers = 0
    total_still_win = 0
    total_became_lose = 0
    total_fby = 0
    total_fby_win = 0
    total_fby_lose = 0
    total_volspike = 0
    total_volspike_win = 0
    total_volspike_lose = 0
    daily_details = []

    for date in sorted(paired_dates.keys()):
        reports_list = paired_dates[date]
        s1 = next(r for r in reports_list if r['type']=='sesi1')
        as_ = next(r for r in reports_list if r['type']=='akhir_sesi')

        s1_g = {s['stock'] for s in s1.get('gainer', [])}
        s1_f = {s['stock'] for s in s1.get('foreign_buy_yesterday', [])}
        s1_v = {s['stock'] for s in s1.get('volume_spike', [])}
        as_g = {s['stock'] for s in as_.get('gainer', [])}
        as_l = {s['stock'] for s in as_.get('loser', [])}

        still_win = s1_g & as_g
        became_lose = s1_g & as_l
        fby_win = s1_f & as_g
        fby_lose = s1_f & as_l
        vol_win = s1_v & as_g
        vol_lose = s1_v & as_l

        total_s1_gainers += len(s1_g)
        total_still_win += len(still_win)
        total_became_lose += len(became_lose)
        total_fby += len(s1_f)
        total_fby_win += len(fby_win)
        total_fby_lose += len(fby_lose)
        total_volspike += len(s1_v)
        total_volspike_win += len(vol_win)
        total_volspike_lose += len(vol_lose)

        daily_details.append({
            'date': date,
            's1_ihsg': s1.get('ihsg_change'),
            'as_ihsg': as_.get('ihsg_change'),
            's1_gainers': list(s1_g),
            'still_win': list(still_win),
            'became_lose': list(became_lose),
            'disappeared': list(s1_g - still_win - became_lose),
            'fby_signals': list(s1_f),
            'fby_win': list(fby_win),
            'vol_spike': list(s1_v),
            'vol_win': list(vol_win),
        })

    g_win_rate = round(total_still_win / max(total_s1_gainers, 1) * 100, 1)
    g_lose_rate = round(total_became_lose / max(total_s1_gainers, 1) * 100, 1)
    g_neutral = total_s1_gainers - total_still_win - total_became_lose
    g_neutral_rate = round(g_neutral / max(total_s1_gainers, 1) * 100, 1)

    fby_win_rate = round(total_fby_win / max(total_fby, 1) * 100, 1)
    vol_win_rate = round(total_volspike_win / max(total_volspike, 1) * 100, 1)

    return {
        'status': 'ok',
        'summary': {
            'paired_days': len(paired_dates),
            'total_s1_gainers': total_s1_gainers,
            'total_fby': total_fby,
            'total_volspike': total_volspike,
        },
        'strategies': [
            {
                'id': 's1_gainers',
                'name': 'Beli Top Gainer Sesi 1 -> Tahan ke Akhir Sesi',
                'trades': total_s1_gainers,
                'wins': total_still_win,
                'losses': total_became_lose,
                'neutral': g_neutral,
                'win_rate': g_win_rate,
                'loss_rate': g_lose_rate,
                'neutral_rate': g_neutral_rate,
                'verdict': 'REKOMENDASI' if g_win_rate > 50 else 'HINDAKI',
                'color': 'var(--success)' if g_win_rate > 50 else 'var(--danger)',
            },
            {
                'id': 'fby',
                'name': 'Beli Sesi 1 Naik Setelah Asing Beli -> Tahan ke Akhir Sesi',
                'trades': total_fby,
                'wins': total_fby_win,
                'losses': total_fby_lose,
                'neutral': total_fby - total_fby_win - total_fby_lose,
                'win_rate': fby_win_rate,
                'verdict': 'MODERAT' if fby_win_rate > 10 else 'LEMAH',
                'color': 'var(--warning)' if fby_win_rate > 10 else 'var(--muted)',
            },
            {
                'id': 'volspike',
                'name': 'Beli Sesi 1 Lonjakan Volume -> Tahan ke Akhir Sesi',
                'trades': total_volspike,
                'wins': total_volspike_win,
                'losses': total_volspike_lose,
                'neutral': total_volspike - total_volspike_win - total_volspike_lose,
                'win_rate': vol_win_rate,
                'verdict': 'MODERAT' if vol_win_rate > 10 else 'LEMAH',
                'color': 'var(--warning)' if vol_win_rate > 10 else 'var(--muted)',
            },
        ],
        'daily': daily_details[-30:],  # last 30 days
    }




@router.get("/broker-summary/stocks")
def broker_summary_stocks():
    """List stocks that have broker_summary data."""
    from app.database.database import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT stock_code, COUNT(*) as entries, 
                   MAX(period_from) as latest_from, MAX(period_to) as latest_to
            FROM broker_summary
            GROUP BY stock_code
            ORDER BY stock_code
        """).fetchall()
        stocks = []
        for r in rows:
            if hasattr(r, 'keys'):
                stocks.append(dict(r))
            else:
                stocks.append({
                    'stock_code': r[0],
                    'entries': r[1],
                    'latest_from': str(r[2]) if r[2] else None,
                    'latest_to': str(r[3]) if r[3] else None,
                })
        return {'status': 'ok', 'stocks': stocks}


@router.get("/broker-summary/{stock_code}")
def broker_summary(stock_code: str):
    """Get aggregated broker summary data for a stock."""
    from app.database.database import get_db

    with get_db() as conn:
        # Get period (optional — data from upload may not have it)
        rows = conn.execute("""
            SELECT DISTINCT period_from, period_to, is_gross
            FROM broker_summary
            WHERE stock_code = ?
            ORDER BY period_from DESC
            LIMIT 1
        """, (stock_code.upper(),)).fetchall()
        
        period_from = None
        period_to = None
        is_gross = False
        if rows:
            row = rows[0]
            period_from = row['period_from'] if hasattr(row, '__getitem__') else row[0]
            period_to = row['period_to'] if hasattr(row, '__getitem__') else row[1]
            is_gross = row['is_gross'] if hasattr(row, '__getitem__') else row[2]

        # Buyers
        buyers = conn.execute("""
            SELECT broker_code, lots, value, avg_price
            FROM broker_summary
            WHERE stock_code=? AND side='buy'
            ORDER BY value DESC
        """, (stock_code.upper(),)).fetchall()

        # Sellers
        sellers = conn.execute("""
            SELECT broker_code, lots, value, avg_price
            FROM broker_summary
            WHERE stock_code=? AND side='sell'
            ORDER BY value DESC
        """, (stock_code.upper(),)).fetchall()

        # Convert to dicts
        def row2dict(r):
            if hasattr(r, 'keys'):
                return dict(r)
            return {'broker_code': r[0], 'lots': r[1], 'value': r[2], 'avg_price': r[3]}

        buyers_list = [row2dict(r) for r in buyers]
        sellers_list = [row2dict(r) for r in sellers]

        # Net flow
        bmap = {b['broker_code']: b for b in buyers_list}
        smap = {b['broker_code']: b for b in sellers_list}
        codes = set(list(bmap.keys()) + list(smap.keys()))
        net_flow = []
        for c in sorted(codes):
            bv = bmap.get(c, {}).get('value', 0)
            sv = smap.get(c, {}).get('value', 0)
            net = bv - sv
            net_flow.append({
                'broker_code': c,
                'net': net,
                'buy_value': bv,
                'sell_value': sv,
                'buy_lots': bmap.get(c, {}).get('lots', 0),
                'sell_lots': smap.get(c, {}).get('lots', 0),
            })
        net_flow.sort(key=lambda x: x['net'], reverse=True)

        # Two-way analysis from broker_summary data
        two_way_list = []
        for b in buyers_list:
            bc = b['broker_code']
            sl = smap.get(bc, {})
            b_lots = b.get('lots', 0)
            s_lots = sl.get('lots', 0)
            total_vol = b_lots + s_lots
            if total_vol > 0:
                min_side = min(b_lots, s_lots)
                two_way_pct = (2 * min_side / total_vol) * 100
                two_way_list.append({
                    'broker_code': bc,
                    'buy_lots': b_lots,
                    'sell_lots': s_lots,
                    'total_volume': total_vol,
                    'two_way_percentage': round(two_way_pct, 2),
                })
        # also check sellers not in buyers
        for b in sellers_list:
            bc = b['broker_code']
            if bc not in bmap:
                b_lots = 0
                s_lots = b.get('lots', 0)
                total_vol = b_lots + s_lots
                if total_vol > 0:
                    two_way_list.append({
                        'broker_code': bc,
                        'buy_lots': b_lots,
                        'sell_lots': s_lots,
                        'total_volume': total_vol,
                        'two_way_percentage': 0.0,
                    })
        two_way_list.sort(key=lambda x: x['total_volume'], reverse=True)
        top_two_way = max(two_way_list, key=lambda x: x['two_way_percentage']) if two_way_list else None
        most_one_way = min(two_way_list, key=lambda x: x['two_way_percentage']) if two_way_list else None

        total_buy = sum(b['value'] for b in buyers_list)
        total_sell = sum(b['value'] for b in sellers_list)

        # Crossing analysis from broker_meta
        crossing_info = None
        try:
            crossing_info = conn.execute("""
                SELECT meta_value FROM broker_meta
                WHERE stock_code=? AND meta_key='crossing_analysis'
                ORDER BY created_at DESC LIMIT 1
            """, (stock_code.upper(),)).fetchone()
            logger.info(f"broker_meta query for {stock_code}: {crossing_info}")
        except Exception as e:
            logger.error(f"broker_meta query error: {e}")

        crossings_data = {}
        if crossing_info:
            cv = crossing_info[0] if hasattr(crossing_info, '__getitem__') else crossing_info['meta_value']
            if isinstance(cv, str):
                crossings_data = json.loads(cv)
            else:
                crossings_data = cv

        pc = crossings_data.get('potential_crossings', [])
        tw = crossings_data.get('two_way_brokers', [])
        avg_spread = crossings_data.get('average_spread', 0)
        widest = None
        if pc:
            w = max(pc, key=lambda x: abs(x.get('spread', 0)))
            widest = {
                'buyer_broker': w.get('buyer_broker', ''),
                'seller_broker': w.get('seller_broker', ''),
                'spread': w.get('spread', 0),
            }

        return {
            'status': 'ok',
            'stock_code': stock_code.upper(),
            'period_from': str(period_from) if period_from else None,
            'period_to': str(period_to) if period_to else None,
            'is_gross': bool(is_gross),
            'buyer_count': len(buyers_list),
            'seller_count': len(sellers_list),
            'total_buy_value': format(int(total_buy), ','),
            'total_sell_value': format(int(total_sell), ','),
            'net_flow': net_flow,
            'buyers': buyers_list,
            'sellers': sellers_list,
            'crossing_count': len(pc),
            'crossings': pc[:200],
            'top_two_way': top_two_way,
            'most_one_way': most_one_way,
            'avg_spread': avg_spread,
            'widest_crossing': widest,
        }


@router.get("/broker-summary/{stock_code}/recommendation")
def broker_recommendation(stock_code: str):
    """Generate AI recommendation signals from broker data.
    
    Classifies brokers -> Smart Money / Institusi Lokal / Retail.
    Generates signals: retail concurrency, smart money flow, divergence.
    """
    from app.database.broker_models import (
        get_broker_category, get_broker_category_label
    )
    from app.database.database import get_db

    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT period_from, period_to
            FROM broker_summary WHERE stock_code = ?
            ORDER BY period_from DESC LIMIT 1
        """, (stock_code.upper(),)).fetchall()
        if not rows:
            return {"status": "error", "message": f"No broker data for {stock_code.upper()}"}

        row = rows[0]
        period_from = row['period_from'] if hasattr(row, '__getitem__') else row[0]
        period_to = row['period_to'] if hasattr(row, '__getitem__') else row[1]

        # Get all transactions
        buyers = conn.execute("""
            SELECT broker_code, lots, value, avg_price
            FROM broker_summary WHERE stock_code=? AND side='buy'
            ORDER BY value DESC
        """, (stock_code.upper(),)).fetchall()

        sellers = conn.execute("""
            SELECT broker_code, lots, value, avg_price
            FROM broker_summary WHERE stock_code=? AND side='sell'
            ORDER BY value DESC
        """, (stock_code.upper(),)).fetchall()

    def r2d(r):
        if hasattr(r, 'keys'):
            return dict(r)
        return {'broker_code': r[0], 'lots': r[1], 'value': r[2], 'avg_price': r[3]}

    buyers_list = [r2d(r) for r in buyers]
    sellers_list = [r2d(r) for r in sellers]

    bmap = {b['broker_code']: b for b in buyers_list}
    smap = {b['broker_code']: b for b in sellers_list}
    codes = sorted(set(list(bmap.keys()) + list(smap.keys())))

    # Classify each broker
    classified = []
    by_category = {"smart_money": [], "institutional": [], "retail": [], "unknown": []}

    for c in codes:
        cat = get_broker_category(c)
        label, icon, color = get_broker_category_label(cat)
        bv = bmap.get(c, {}).get('value', 0)
        sv = smap.get(c, {}).get('value', 0)
        bl = bmap.get(c, {}).get('lots', 0)
        sl = smap.get(c, {}).get('lots', 0)
        net = bv - sv

        entry = {
            "broker_code": c,
            "category": cat,
            "label": label,
            "icon": icon,
            "buy_value": bv,
            "sell_value": sv,
            "net": net,
            "buy_lots": bl,
            "sell_lots": sl,
            "is_buyer": c in bmap,
            "is_seller": c in smap,
        }
        classified.append(entry)
        if cat in by_category:
            by_category[cat].append(entry)

    # Aggregated stats by category
    def agg(cat_list):
        total_buy = sum(b['buy_value'] for b in cat_list)
        total_sell = sum(b['sell_value'] for b in cat_list)
        total_buy_lots = sum(b['buy_lots'] for b in cat_list)
        total_sell_lots = sum(b['sell_lots'] for b in cat_list)
        net = total_buy - total_sell
        brokers = list(set(b['broker_code'] for b in cat_list))
        return {
            "total_buy_value": total_buy,
            "total_sell_value": total_sell,
            "net_value": net,
            "total_buy_lots": total_buy_lots,
            "total_sell_lots": total_sell_lots,
            "broker_count": len(brokers),
            "brokers": sorted(brokers),
        }

    smart = agg(by_category["smart_money"])
    inst = agg(by_category["institutional"])
    retail = agg(by_category["retail"])

    # === SIGNAL GENERATION ===

    signals = []

    # 1) Retail concurrency - how many retail brokers buy together
    retail_buyers = [b for b in by_category["retail"] if b['is_buyer'] and b['buy_value'] > 0]
    retail_sellers = [b for b in by_category["retail"] if b['is_seller'] and b['sell_value'] > 0]
    retail_buyer_count = len(retail_buyers)
    retail_seller_count = len(retail_sellers)

    if retail_buyer_count >= 3:
        signals.append({
            "type": "retail_concurrency_buy",
            "label": "👥 Retail Ramai Beli",
            "message": f"{retail_buyer_count} broker retail kompak beli ({', '.join(b['broker_code'] for b in retail_buyers[:5])})",
            "sentiment": "positive",
            "strength": min(retail_buyer_count / 3, 1.0),
        })
    if retail_seller_count >= 3:
        signals.append({
            "type": "retail_concurrency_sell",
            "label": "👥 Retail Ramai Jual",
            "message": f"{retail_seller_count} broker retail kompak jual ({', '.join(b['broker_code'] for b in retail_sellers[:5])})",
            "sentiment": "negative",
            "strength": min(retail_seller_count / 3, 1.0),
        })

    # 2) Smart money flow
    if smart["net_value"] > 0:
        signals.append({
            "type": "smart_money_buy",
            "label": "🌍 Smart Money Beli",
            "message": f"Smart Money net buy Rp{smart['net_value']:,.0f} dari {smart['broker_count']} broker asing",
            "sentiment": "positive",
            "strength": min(smart["net_value"] / (smart["total_buy_value"] + 1) * 2, 1.0),
        })
    elif smart["net_value"] < 0:
        signals.append({
            "type": "smart_money_sell",
            "label": "🌍 Smart Money Jual",
            "message": f"Smart Money net sell Rp{abs(smart['net_value']):,.0f} dari {smart['broker_count']} broker asing",
            "sentiment": "negative",
            "strength": min(abs(smart["net_value"]) / (smart["total_sell_value"] + 1) * 2, 1.0),
        })

    # 3) Institutional flow
    if inst["net_value"] > 0:
        signals.append({
            "type": "institutional_buy",
            "label": "🏦 Institusi Lokal Beli",
            "message": f"Institusi lokal net buy Rp{inst['net_value']:,.0f} ({inst['broker_count']} broker)",
            "sentiment": "positive",
            "strength": 0.6,
        })
    elif inst["net_value"] < 0:
        signals.append({
            "type": "institutional_sell",
            "label": "🏦 Institusi Lokal Jual",
            "message": f"Institusi lokal net sell Rp{abs(inst['net_value']):,.0f} ({inst['broker_count']} broker)",
            "sentiment": "negative",
            "strength": 0.6,
        })

    # 4) Retail vs Smart Money divergence
    if retail["net_value"] > 0 and smart["net_value"] < 0:
        signals.append({
            "type": "divergence_retail_buy_smart_sell",
            "label": "!️ Divergence",
            "message": f"Retail beli (Rp{retail['net_value']:,.0f}) tapi Smart Money jual (Rp{abs(smart['net_value']):,.0f}) - hati-hati",
            "sentiment": "warning",
            "strength": 0.8,
        })
    elif retail["net_value"] < 0 and smart["net_value"] > 0:
        signals.append({
            "type": "divergence_retail_sell_smart_buy",
            "label": "[OK] Smart Money Akumulasi",
            "message": f"Smart Money beli (Rp{smart['net_value']:,.0f}) sementara retail jual - sinyal bullish",
            "sentiment": "positive",
            "strength": 0.9,
        })

    # 5) Retail sentiment (total)
    retail_total_value = retail["total_buy_value"] + retail["total_sell_value"]
    if retail_total_value > 0:
        retail_buy_ratio = retail["total_buy_value"] / retail_total_value
        if retail_buy_ratio > 0.7:
            signals.append({
                "type": "retail_euphoria",
                "label": "🔥 Retail Euphoria",
                "message": f"{retail_buy_ratio*100:.0f}% transaksi retail adalah BUY - euforia, waspadai reversal",
                "sentiment": "warning",
                "strength": 0.7,
            })
        elif retail_buy_ratio < 0.3:
            signals.append({
                "type": "retail_panic",
                "label": "😨 Retail Panic",
                "message": f"{(1-retail_buy_ratio)*100:.0f}% transaksi retail adalah SELL - panic selling, potensi bottom",
                "sentiment": "warning",
                "strength": 0.7,
            })

    # === OVERALL RECOMMENDATION ===
    total_net = smart["net_value"] + inst["net_value"] + retail["net_value"]
    retail_buy_ratio = 0.5  # default neutral
    if smart["net_value"] > 0 and retail["net_value"] > 0:
        overall = "BUY"
        reason = "Smart Money + Retail sama-sama beli"
    elif smart["net_value"] > 0 and retail["net_value"] < 0:
        overall = "ACCUMULATE"
        reason = "Smart Money beli, retail jual - akumulasi diam-diam"
    elif smart["net_value"] < 0 and retail["net_value"] > 0:
        overall = "WATCH"
        reason = "Smart Money jual, retail beli - waspadai distribusi"
    elif smart["net_value"] < 0 and inst["net_value"] < 0:
        overall = "SELL"
        reason = "Smart Money + Institusi kompak jual"
    else:
        overall = "HOLD"
        reason = "Belum ada sinyal jelas dari broker data"

    # Calculate confidence based on signal strength
    avg_strength = sum(s.get("strength", 0) for s in signals) / max(len(signals), 1)
    confidence = min(95, max(15, int(avg_strength * 100)))

    return {
        "status": "ok",
        "stock_code": stock_code.upper(),
        "period_from": str(period_from) if period_from else None,
        "period_to": str(period_to) if period_to else None,
        "recommendation": overall,
        "confidence": confidence,
        "reason": reason,
        "signals": signals,
        "categories": {
            "smart_money": smart,
            "institutional": inst,
            "retail": retail,
        },
        "classified": [
            c for c in classified if c["buy_value"] > 0 or c["sell_value"] > 0
        ],
        "trade_summary": {
            "total_buy_value": sum(c["buy_value"] for c in classified),
            "total_sell_value": sum(c["sell_value"] for c in classified),
        }
    }


@router.get("/crossing/summary/{stock_code}")
def crossing_summary(stock_code: str):
    import mysql.connector
    conn = mysql.connector.connect(
        host='localhost', user='root', password='', database='analisa_saham'
    )
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT broker_code, SUM(lots) as total_lots, SUM(value) as total_value
        FROM broker_summary
        WHERE stock_code = %s
        GROUP BY broker_code
        ORDER BY total_value DESC
    """, (stock_code.upper(),))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return {"status": "ok", "data": data}
    brokers = {}

    for c in pc:
        s = abs(c.get('spread', 0))
        if s < 1:
            dist["<1%"] += 1
        elif s <= 3:
            dist["1-3%"] += 1
        else:
            dist[">3%"] += 1

        b = c.get('buyer_broker')
        if b:
            brokers[b] = brokers.get(b, 0) + 1
        s_b = c.get('seller_broker')
        if s_b:
            brokers[s_b] = brokers.get(s_b, 0) + 1

    top_brokers = sorted(brokers.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "status": "ok",
        "spread_dist": dist,
        "top_brokers": top_brokers,
        "total_crossing": len(pc),
    }
