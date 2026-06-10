from datetime import datetime
from typing import Optional

import pandas as pd

from app.services.stock_service import (
    fetch_intraday_data,
    get_opening_range,
    STOCK_LIST,
)
from app.database.foreign_flow_models import get_accumulation_status


def _today_df(df: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for today's data only, fallback to last trading day."""
    if df is None or df.empty:
        return df
    today = pd.Timestamp.now().normalize()
    today_data = df[df.index.normalize() == today]
    if not today_data.empty:
        return today_data
    # Fallback: last trading day
    last_day = df.index.normalize().max()
    return df[df.index.normalize() == last_day]


class BPJSStrategy:

    def get_entry_signal(self, stock_code: str, df_intraday: pd.DataFrame) -> dict:
        if df_intraday is None or df_intraday.empty:
            return {"action": "WAIT", "reason": "No intraday data"}

        today_data = _today_df(df_intraday)
        if today_data.empty:
            return {"action": "WAIT", "reason": "Market closed — no today data"}

        open_range = get_opening_range(df_intraday)
        if "error" in open_range:
            return {"action": "WAIT", "reason": open_range["error"]}

        current_price = float(today_data["Close"].iloc[-1])
        breakout = current_price > open_range["open_range_high"]
        volume_ratio = open_range["volume_ratio"]
        gap_pct = open_range["gap_pct"]

        foreign_status = None
        try:
            acc = get_accumulation_status(stock_code)
            if acc:
                foreign_status = acc.get("status", "neutral")
        except Exception:
            foreign_status = None

        if gap_pct > 3.0:
            return {
                "action": "WAIT",
                "stock_code": stock_code,
                "reason": "Gap terlalu besar, risiko reversal",
                "entry_price": 0,
                "target_profit": 0,
                "cut_loss": 0,
                "open_range": open_range,
                "volume_ratio": volume_ratio,
                "foreign_flow_status": foreign_status,
                "confidence": 0,
            }

        if not breakout:
            return {
                "action": "WAIT",
                "stock_code": stock_code,
                "reason": "Harga belum breakout opening range",
                "entry_price": round(current_price, 2),
                "target_profit": round(current_price * 1.015, 2),
                "cut_loss": round(current_price * 0.993, 2),
                "open_range": open_range,
                "volume_ratio": volume_ratio,
                "foreign_flow_status": foreign_status,
                "confidence": 0,
            }

        if volume_ratio < 1.5:
            return {
                "action": "WAIT",
                "stock_code": stock_code,
                "reason": "Volume tidak mencukupi",
                "entry_price": round(current_price, 2),
                "target_profit": round(current_price * 1.015, 2),
                "cut_loss": round(current_price * 0.993, 2),
                "open_range": open_range,
                "volume_ratio": volume_ratio,
                "foreign_flow_status": foreign_status,
                "confidence": 20,
            }

        if foreign_status == "distributing":
            return {
                "action": "WAIT",
                "stock_code": stock_code,
                "reason": "Asing jual, hindari",
                "entry_price": round(current_price, 2),
                "target_profit": round(current_price * 1.015, 2),
                "cut_loss": round(current_price * 0.993, 2),
                "open_range": open_range,
                "volume_ratio": volume_ratio,
                "foreign_flow_status": foreign_status,
                "confidence": 30,
            }

        confidence = 50
        if volume_ratio > 2.0:
            confidence += 10
        if foreign_status == "accumulating":
            confidence += 15
        elif foreign_status == "neutral":
            confidence += 5
        if open_range["range_pct"] < 0.5:
            confidence += 5

        entry_price = open_range["open_range_high"]
        return {
            "action": "ENTER",
            "stock_code": stock_code,
            "reason": "Breakout opening range + volume spike" + (" + asing akumulasi" if foreign_status == "accumulating" else ""),
            "entry_price": round(entry_price, 2),
            "target_profit": round(entry_price * 1.015, 2),
            "cut_loss": round(entry_price * 0.993, 2),
            "open_range": open_range,
            "volume_ratio": volume_ratio,
            "foreign_flow_status": foreign_status,
            "confidence": min(confidence, 99),
        }

    def get_exit_signal(self, entry_price: float, target_profit: float, cut_loss: float, current_price: float, current_time_str: str) -> dict:
        pnl_pct = round((current_price - entry_price) / entry_price * 100, 2)

        if current_price >= target_profit:
            return {
                "action": "EXIT_TP",
                "reason": f"Target profit tercapai ({pnl_pct}%)",
                "current_price": round(current_price, 2),
                "pnl_pct": pnl_pct,
            }

        if current_price <= cut_loss:
            return {
                "action": "EXIT_CL",
                "reason": f"Cut loss triggered ({pnl_pct}%)",
                "current_price": round(current_price, 2),
                "pnl_pct": pnl_pct,
            }

        try:
            t = datetime.strptime(current_time_str.strip(), "%H:%M")
            if t.hour >= 14 and t.minute >= 30:
                return {
                    "action": "EXIT_TIME",
                    "reason": "Market session ends, exit position",
                    "current_price": round(current_price, 2),
                    "pnl_pct": pnl_pct,
                }
        except (ValueError, AttributeError):
            pass

        return {
            "action": "HOLD",
            "reason": "Posisi ditahan, pantau terus",
            "current_price": round(current_price, 2),
            "pnl_pct": pnl_pct,
        }

    def analyze(self, code: str) -> dict:
        df = fetch_intraday_data(code)
        if df is None:
            return {"error": f"No intraday data for {code}"}

        entry_signal = self.get_entry_signal(code, df)
        today_data = _today_df(df)
        current_price = float(today_data["Close"].iloc[-1]) if not today_data.empty else 0

        result = {
            "stock_code": code.upper(),
            "current_price": round(current_price, 2),
            "entry_signal": entry_signal,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if entry_signal["action"] in ("ENTER", "WAIT") and entry_signal.get("entry_price", 0) > 0:
            result["exit_signal"] = self.get_exit_signal(
                entry_price=entry_signal["entry_price"],
                target_profit=entry_signal["target_profit"],
                cut_loss=entry_signal["cut_loss"],
                current_price=current_price,
                current_time_str=datetime.now().strftime("%H:%M"),
            )

        return result

    def scan_candidates(self) -> list[dict]:
        candidates = []
        data_date = None
        top_codes = list(STOCK_LIST.keys())[:10]
        for code in top_codes:
            try:
                df = fetch_intraday_data(code)
                if df is None:
                    continue
                signal = self.get_entry_signal(code, df)
                # Track which day's data
                if data_date is None and not df.empty:
                    data_date = df.index.normalize().max().strftime("%d %b")

                # Get pre-market score even if no ENTER
                today_df = _today_df(df)
                open_range = get_opening_range(df)
                if not today_df.empty and "error" not in open_range:
                    current_price = float(today_df["Close"].iloc[-1])
                    volume_ratio = open_range.get("volume_ratio", 1)
                    near_breakout = current_price > open_range.get("open_range_high", 0) * 0.98
                    try:
                        acc = get_accumulation_status(code)
                        foreign = acc.get("status", "neutral") if acc else "neutral"
                    except Exception:
                        foreign = "neutral"
                    premkt_score = int(volume_ratio * 20)
                    if near_breakout:
                        premkt_score += 20
                    if foreign == "accumulating":
                        premkt_score += 15
                    if code.upper() in STOCK_LIST:
                        signal["stock_name"] = STOCK_LIST.get(code, "")
                    signal["premarket_score"] = min(premkt_score, 99)
                    signal["volume_ratio"] = round(volume_ratio, 1)
                    signal["foreign_flow_status"] = foreign

                if signal["action"] == "ENTER":
                    signal["stock_name"] = STOCK_LIST.get(code, "")
                    candidates.append(signal)
            except Exception:
                continue

        candidates.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        # If no ENTER signals, return pre-market watchlist
        if not candidates:
            watchlist = []
            for code in top_codes:
                try:
                    df = fetch_intraday_data(code)
                    if df is None or df.empty:
                        continue
                    td = _today_df(df)
                    if td.empty or len(td) < 2:
                        continue

                    prices = td["Close"].values
                    current_price = float(prices[-1])
                    opening_prices = td.iloc[:max(1, 6)]  # first ~30min
                    open_high = float(opening_prices["High"].max())
                    open_low = float(opening_prices["Low"].min())
                    first_open = float(opening_prices["Open"].iloc[0])
                    range_size = open_high - open_low
                    range_pct = (range_size / first_open * 100) if first_open else 0
                    opening_vol = int(opening_prices["Volume"].sum())
                    total_vol = int(td["Volume"].sum())
                    total_rows = len(td)
                    avg_vol_per_row = total_vol / total_rows if total_rows else 1
                    n_opening = len(opening_prices)
                    vol_ratio = opening_vol / (avg_vol_per_row * n_opening) if avg_vol_per_row > 0 else 1

                    try:
                        acc = get_accumulation_status(code)
                        foreign = acc.get("status", "neutral") if acc else "neutral"
                    except Exception:
                        foreign = "neutral"

                    score = 0
                    reasons = []
                    if vol_ratio > 1.5:
                        score += 25
                        reasons.append(f"volume {vol_ratio:.1f}x")
                    if current_price > open_high * 0.985:
                        score += 25
                        reasons.append("dekat breakout")
                    if foreign == "accumulating":
                        score += 20
                        reasons.append("asing akumulasi")
                    elif foreign == "neutral":
                        score += 5
                    if range_pct < 0.8:
                        score += 10
                        reasons.append(f"range {range_pct:.2f}%")

                    if score >= 40:
                        watchlist.append({
                            "stock_code": code,
                            "stock_name": STOCK_LIST.get(code, ""),
                            "action": "WATCH",
                            "confidence": min(score, 99),
                            "reason": " | ".join(reasons) if reasons else "Setup potensial",
                            "volume_ratio": round(vol_ratio, 1),
                            "foreign_flow_status": foreign,
                            "current_price": round(current_price, 2),
                            "premarket_score": min(score, 99),
                            "close_price": round(current_price, 2),
                        })
                except Exception:
                    continue
            watchlist.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            return watchlist[:5]

        return candidates
