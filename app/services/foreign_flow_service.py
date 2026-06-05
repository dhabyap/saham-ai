import re
from datetime import datetime
from typing import Optional
import pandas as pd
import requests

from app.database.foreign_flow_models import (
    save_foreign_flow,
    update_accumulation,
)
from app.services.stock_service import STOCK_LIST, fetch_stock_data


_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
})


def fetch_foreign_flow_rti(stock_code: str) -> Optional[dict]:
    stock_code = stock_code.upper().strip()
    code_lower = stock_code.lower()
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [
        f"https://rti.biz.id/emiten/{code_lower}",
        f"https://www.rti.co.id/stock/{stock_code}",
    ]

    for url in urls:
        try:
            r = _session.get(url, timeout=15)
            if r.status_code != 200:
                continue
            html = r.text

            foreign_buy = _extract_number(html, r"(?:foreign.?buy|foreign.?beli|beli.?asing)[:\s]*Rp?\.?\s*([\d.,]+)")
            foreign_sell = _extract_number(html, r"(?:foreign.?sell|foreign.?jual|jual.?asing)[:\s]*Rp?\.?\s*([\d.,]+)")

            if foreign_buy is not None and foreign_sell is not None:
                foreign_net = foreign_buy - foreign_sell
                return {
                    "stock_code": stock_code,
                    "trade_date": today,
                    "foreign_buy": foreign_buy,
                    "foreign_sell": foreign_sell,
                    "foreign_net": foreign_net,
                    "source": "rti",
                }
        except Exception:
            continue

    try:
        r = _session.get("https://www.idx.co.id/", timeout=15)
        if r.status_code == 200:
            html = r.text
            foreign_buy = _extract_number(html, r"(?:foreign.?buy|beli.?asing)[:\s]*Rp?\.?\s*([\d.,]+)")
            foreign_sell = _extract_number(html, r"(?:foreign.?sell|jual.?asing)[:\s]*Rp?\.?\s*([\d.,]+)")
            if foreign_buy is not None and foreign_sell is not None:
                foreign_net = foreign_buy - foreign_sell
                return {
                    "stock_code": stock_code,
                    "trade_date": today,
                    "foreign_buy": foreign_buy,
                    "foreign_sell": foreign_sell,
                    "foreign_net": foreign_net,
                    "source": "idx",
                }
    except Exception:
        pass

    return None


def _extract_number(html: str, pattern: str) -> Optional[float]:
    try:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            raw = m.group(1).replace(".", "").replace(",", ".")
            return float(raw)
    except Exception:
        pass
    return None


def estimate_foreign_flow_from_price(df: pd.DataFrame, stock_code: str) -> dict:
    stock_code = stock_code.upper().strip()
    today = datetime.now().strftime("%Y-%m-%d")

    if df is None or df.empty:
        return {
            "stock_code": stock_code,
            "trade_date": today,
            "foreign_buy": 0,
            "foreign_sell": 0,
            "foreign_net": 0,
            "source": "estimated",
            "confidence": 0.0,
        }

    latest = df.iloc[-1]
    close = latest.get("Close", 0) or 0
    volume = latest.get("Volume", 0) or 0
    open_price = latest.get("Open", 0) or 0

    total_volume_estimate = volume * close

    avg_volume = df["Volume"].tail(20).mean() if len(df) >= 20 else df["Volume"].mean()
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

    is_green = close > open_price
    volume_spike = volume_ratio > 1.5

    if volume_spike and is_green:
        foreign_buy = total_volume_estimate * 0.6
        foreign_sell = total_volume_estimate * 0.4
        confidence = 0.5
    elif volume_spike and not is_green:
        foreign_buy = total_volume_estimate * 0.4
        foreign_sell = total_volume_estimate * 0.6
        confidence = 0.5
    else:
        foreign_buy = total_volume_estimate * 0.5
        foreign_sell = total_volume_estimate * 0.5
        confidence = 0.3

    foreign_net = foreign_buy - foreign_sell

    return {
        "stock_code": stock_code,
        "trade_date": today,
        "foreign_buy": foreign_buy,
        "foreign_sell": foreign_sell,
        "foreign_net": foreign_net,
        "total_volume": total_volume_estimate,
        "last_price": close,
        "source": "estimated",
        "confidence": confidence,
    }


def fetch_and_save_foreign_flow(stock_code: str) -> bool:
    stock_code = stock_code.upper().strip()
    data = fetch_foreign_flow_rti(stock_code)

    if data is None:
        stock_data = fetch_stock_data(stock_code, period="1mo")
        if stock_data is None:
            return False
        df = stock_data.get("history")
        if df is None or df.empty:
            return False
        data = estimate_foreign_flow_from_price(df, stock_code)

    if data is None:
        return False

    save_foreign_flow([data])
    update_accumulation(stock_code, data["trade_date"])
    return True


def sync_all_foreign_flow(stock_codes: list = None) -> dict:
    if stock_codes is None:
        stock_codes = list(STOCK_LIST.keys())

    success = 0
    failed = 0
    errors = []

    for code in stock_codes:
        try:
            ok = fetch_and_save_foreign_flow(code)
            if ok:
                success += 1
            else:
                failed += 1
                errors.append(f"{code}: failed")
        except Exception as e:
            failed += 1
            errors.append(f"{code}: {str(e)}")

    return {
        "success": success,
        "failed": failed,
        "total": len(stock_codes),
        "errors": errors,
    }
