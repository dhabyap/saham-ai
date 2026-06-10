"""Treemap service — market heatmap by sector."""
import time
from datetime import datetime
from typing import Optional

from app.constants import SECTOR_MAP
from app.http_client import get_http_client


# Simple in-memory cache
_cache: Optional[dict] = None
_cache_ts: float = 0
_CACHE_TTL = 120  # 2 minutes


def get_treemap_data(force_refresh: bool = False) -> dict:
    """Build treemap: stocks grouped by sector with change% + size proxy."""
    global _cache, _cache_ts
    now = time.time()
    if not force_refresh and _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

    sectors = {}
    client = get_http_client()
    codes = list(SECTOR_MAP.keys())

    for code in codes:
        try:
            ycode = f"{code}.JK"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ycode}?range=5d&interval=1d"
            r = client.get(url, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            result = data["chart"]["result"]
            if not result:
                continue
            result = result[0]
            ts = result.get("timestamp", [])
            quotes = result["indicators"]["quote"][0]
            closes = quotes.get("close", [])
            opens = quotes.get("open", [])
            volumes = quotes.get("volume", [])
            highs = quotes.get("high", [])
            lows = quotes.get("low", [])

            if not closes or len(closes) < 2:
                continue

            # Clean None values
            clean = [(o, h, l, c, v) for o, h, l, c, v in zip(opens, highs, lows, closes, volumes)
                     if all(x is not None for x in (o, h, l, c, v))]
            if len(clean) < 2:
                continue

            latest = clean[-1]
            prev = clean[-2]
            o, h, l, c, v = latest
            change_pct = ((c - prev[3]) / prev[3]) * 100 if prev[3] else 0

            sector = SECTOR_MAP.get(code, "Other")
            if sector not in sectors:
                sectors[sector] = {"name": sector, "stocks": []}

            sectors[sector]["stocks"].append({
                "code": code,
                "close": round(c, 0),
                "change_pct": round(change_pct, 2),
                "volume": int(v),
                "size": round(c * v, 0),  # market cap proxy
                "open": round(o, 0),
                "high": round(h, 0),
                "low": round(l, 0),
            })
            time.sleep(0.15)  # rate limit buffer
        except Exception:
            continue

    # Sort stocks within each sector by size desc
    for s in sectors.values():
        s["stocks"].sort(key=lambda x: x["size"], reverse=True)
        # Total sector change = weighted avg by size
        total_size = sum(st["size"] for st in s["stocks"])
        if total_size:
            s["change_pct"] = round(
                sum(st["change_pct"] * st["size"] for st in s["stocks"]) / total_size, 2
            )
        else:
            s["change_pct"] = 0
        s["total_size"] = sum(st["size"] for st in s["stocks"])
        s["stock_count"] = len(s["stocks"])

    result = {
        "sectors": list(sectors.values()),
        "total_stocks": sum(s["stock_count"] for s in sectors.values()),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "last_updated": datetime.now().isoformat(),
    }

    _cache = result
    _cache_ts = now
    return result
