"""Broker tracking models — identify foreign vs domestic broker activity"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
from app.database.database import get_db, DB_TYPE


KNOWN_FOREIGN_BROKERS = {
    "CGS-CIMB": "CGS-CIMB Sekuritas",
    "CREDIT SUISSE": "Credit Suisse Sekuritas",
    "DBS": "DBS Vickers Sekuritas",
    "GOLDMAN": "Goldman Sachs",
    "HSBC": "HSBC Sekuritas",
    "JPMORGAN": "JP Morgan Sekuritas",
    "MORGAN": "Morgan Stanley",
    "MACQUARIE": "Macquarie Sekuritas",
    "NOMURA": "Nomura Sekuritas",
    "UBS": "UBS Sekuritas",
    "BNP": "BNP Paribas",
    "DEUTSCHE": "Deutsche Bank",
    "CITI": "Citigroup Sekuritas",
    "CLSA": "CLSA Sekuritas",
    "KEPPEL": "Keppel Sekuritas",
    "MIRAE": "Mirae Asset Sekuritas",
    "SAMSUNG": "Samsung Sekuritas",
    "DAEWOO": "Daewoo Sekuritas",
    "YUANTA": "Yuanta Sekuritas",
    "RHB": "RHB Sekuritas",
    "MAYBANK": "Maybank Sekuritas",
    "OCBC": "OCBC Sekuritas",
    "UOB": "UOB Kay Hian",
    "KIM": "Kim Eng Sekuritas",
    "TRIMEGAH": "Trimegah Sekuritas",
}


def _sql():
    return """
    CREATE TABLE IF NOT EXISTS known_brokers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker_code TEXT UNIQUE NOT NULL,
        broker_name TEXT NOT NULL,
        is_foreign INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS broker_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        broker_code TEXT NOT NULL,
        buy_volume INTEGER DEFAULT 0,
        sell_volume INTEGER DEFAULT 0,
        buy_value REAL DEFAULT 0,
        sell_value REAL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(stock_code, trade_date, broker_code)
    );
    """


def init_broker_db():
    """Create tables and seed known brokers."""
    with get_db() as conn:
        conn.executescript(_sql())
        _seed_brokers(conn)


def _seed_brokers(conn):
    """Insert known foreign brokers if not exist."""
    for code, name in KNOWN_FOREIGN_BROKERS.items():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO known_brokers (broker_code, broker_name, is_foreign) VALUES (?, ?, 1)",
                (code, name),
            )
        except Exception:
            pass


def save_broker_transactions(stock_code: str, trade_date: str, transactions: list[dict]) -> int:
    """Save broker transactions. Returns count saved."""
    saved = 0
    with get_db() as conn:
        for t in transactions:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO broker_transactions
                       (stock_code, trade_date, broker_code, buy_volume, sell_volume, buy_value, sell_value)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stock_code.upper(),
                        trade_date,
                        t.get("broker_code", "").upper(),
                        t.get("buy_volume", 0),
                        t.get("sell_volume", 0),
                        t.get("buy_value", 0),
                        t.get("sell_value", 0),
                    ),
                )
                saved += 1
            except Exception:
                continue
    return saved


def get_broker_transactions(stock_code: str, trade_date: str = None) -> list[dict]:
    """Get broker transactions for a stock, optionally filtered by date."""
    with get_db() as conn:
        if trade_date:
            cur = conn.execute(
                """SELECT bt.*, kb.is_foreign, kb.broker_name
                   FROM broker_transactions bt
                   LEFT JOIN known_brokers kb ON bt.broker_code = kb.broker_code
                   WHERE bt.stock_code = ? AND bt.trade_date = ?
                   ORDER BY (bt.buy_value + bt.sell_value) DESC""",
                (stock_code.upper(), trade_date),
            )
        else:
            cur = conn.execute(
                """SELECT bt.*, kb.is_foreign, kb.broker_name
                   FROM broker_transactions bt
                   LEFT JOIN known_brokers kb ON bt.broker_code = kb.broker_code
                   WHERE bt.stock_code = ?
                   ORDER BY bt.trade_date DESC, (bt.buy_value + bt.sell_value) DESC""",
                (stock_code.upper(),),
            )
        return [dict(r) for r in cur.fetchall()]


def calculate_broker_foreign_net(stock_code: str, trade_date: str) -> dict:
    """Calculate net foreign buy/sell from broker transactions."""
    rows = get_broker_transactions(stock_code, trade_date)
    if not rows:
        return {"foreign_buy": 0, "foreign_sell": 0, "foreign_net": 0, "domestic_buy": 0, "domestic_sell": 0, "total": 0}

    foreign_buy = sum(r.get("buy_value", 0) for r in rows if r.get("is_foreign"))
    foreign_sell = sum(r.get("sell_value", 0) for r in rows if r.get("is_foreign"))
    domestic_buy = sum(r.get("buy_value", 0) for r in rows if not r.get("is_foreign"))
    domestic_sell = sum(r.get("sell_value", 0) for r in rows if not r.get("is_foreign"))

    return {
        "foreign_buy": foreign_buy,
        "foreign_sell": foreign_sell,
        "foreign_net": foreign_buy - foreign_sell,
        "domestic_buy": domestic_buy,
        "domestic_sell": domestic_sell,
        "total": foreign_buy + foreign_sell + domestic_buy + domestic_sell,
    }


def get_broker_accumulation_summary(stock_code: str, days: int = 5) -> Optional[dict]:
    """Get multi-day foreign net trend from broker data."""
    with get_db() as conn:
        cur = conn.execute(
            """SELECT bt.trade_date,
                      SUM(CASE WHEN kb.is_foreign = 1 THEN bt.buy_value ELSE 0 END) as f_buy,
                      SUM(CASE WHEN kb.is_foreign = 1 THEN bt.sell_value ELSE 0 END) as f_sell,
                      SUM(CASE WHEN kb.is_foreign = 1 THEN bt.buy_value - bt.sell_value ELSE 0 END) as f_net
               FROM broker_transactions bt
               LEFT JOIN known_brokers kb ON bt.broker_code = kb.broker_code
               WHERE bt.stock_code = ?
               GROUP BY bt.trade_date
               ORDER BY bt.trade_date DESC
               LIMIT ?""",
            (stock_code.upper(), days),
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return None

    total_net = sum(r["f_net"] for r in rows)
    accumulation_days = sum(1 for r in rows if r["f_net"] > 0)

    if accumulation_days >= days * 0.6:
        status = "accumulating"
    elif accumulation_days <= days * 0.3:
        status = "distributing"
    else:
        status = "neutral"

    return {
        "stock_code": stock_code.upper(),
        "days": len(rows),
        "total_net": total_net,
        "accumulation_days": accumulation_days,
        "distribution_days": len(rows) - accumulation_days,
        "status": status,
        "daily": rows,
    }


init_broker_db()
