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
    """Filter dataframe for today's data only."""
    if df is None or df.empty:
        return df
    today = pd.Timestamp.now().normalize()
    return df[df.index.normalize() == today]


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
        top_codes = list(STOCK_LIST.keys())[:10]
        for code in top_codes:
            try:
                df = fetch_intraday_data(code)
                if df is None:
                    continue
                signal = self.get_entry_signal(code, df)
                if signal["action"] == "ENTER":
                    signal["stock_name"] = STOCK_LIST.get(code, "")
                    candidates.append(signal)
            except Exception:
                continue

        candidates.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return candidates
