from datetime import datetime, timedelta
from typing import Optional
from app.database.database import get_db, DB_TYPE


def _mysql_sql():
    return """
        CREATE TABLE IF NOT EXISTS foreign_flow (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(50) NOT NULL,
            trade_date VARCHAR(20) NOT NULL,
            foreign_buy DOUBLE DEFAULT 0,
            foreign_sell DOUBLE DEFAULT 0,
            foreign_net DOUBLE DEFAULT 0,
            domestic_buy DOUBLE DEFAULT 0,
            domestic_sell DOUBLE DEFAULT 0,
            total_volume DOUBLE DEFAULT 0,
            foreign_buy_volume INT DEFAULT 0,
            foreign_sell_volume INT DEFAULT 0,
            last_price DOUBLE DEFAULT 0,
            source VARCHAR(20) DEFAULT "rti",
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_code, trade_date)
        );

        CREATE TABLE IF NOT EXISTS foreign_accumulation (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(50) NOT NULL,
            trade_date VARCHAR(20) NOT NULL,
            cumulative_net DOUBLE DEFAULT 0,
            accumulation_days INT DEFAULT 0,
            distribution_days INT DEFAULT 0,
            avg_net_5d DOUBLE DEFAULT 0,
            avg_net_20d DOUBLE DEFAULT 0,
            status VARCHAR(20) DEFAULT "neutral",
            strength VARCHAR(20) DEFAULT "weak",
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_code, trade_date)
        );
    """


def _sqlite_sql():
    return """
        CREATE TABLE IF NOT EXISTS foreign_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            foreign_buy REAL DEFAULT 0,
            foreign_sell REAL DEFAULT 0,
            foreign_net REAL DEFAULT 0,
            domestic_buy REAL DEFAULT 0,
            domestic_sell REAL DEFAULT 0,
            total_volume REAL DEFAULT 0,
            foreign_buy_volume INTEGER DEFAULT 0,
            foreign_sell_volume INTEGER DEFAULT 0,
            last_price REAL DEFAULT 0,
            source TEXT DEFAULT "rti",
            created_at TEXT DEFAULT (datetime("now", "localtime")),
            UNIQUE(stock_code, trade_date)
        );

        CREATE TABLE IF NOT EXISTS foreign_accumulation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            cumulative_net REAL DEFAULT 0,
            accumulation_days INTEGER DEFAULT 0,
            distribution_days INTEGER DEFAULT 0,
            avg_net_5d REAL DEFAULT 0,
            avg_net_20d REAL DEFAULT 0,
            status TEXT DEFAULT "neutral",
            strength TEXT DEFAULT "weak",
            created_at TEXT DEFAULT (datetime("now", "localtime")),
            UNIQUE(stock_code, trade_date)
        );
    """


def init_foreign_flow_db():
    with get_db() as conn:
        sql = _mysql_sql() if DB_TYPE == "mysql" else _sqlite_sql()
        conn.executescript(sql)


def save_foreign_flow(data: list[dict]):
    with get_db() as conn:
        for row in data:
            conn.execute(
                """INSERT OR REPLACE INTO foreign_flow
                   (stock_code, trade_date, foreign_buy, foreign_sell, foreign_net,
                    domestic_buy, domestic_sell, total_volume, foreign_buy_volume,
                    foreign_sell_volume, last_price, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row.get("stock_code", "").upper(),
                    row.get("trade_date", ""),
                    row.get("foreign_buy", 0),
                    row.get("foreign_sell", 0),
                    row.get("foreign_net", 0),
                    row.get("domestic_buy", 0),
                    row.get("domestic_sell", 0),
                    row.get("total_volume", 0),
                    row.get("foreign_buy_volume", 0),
                    row.get("foreign_sell_volume", 0),
                    row.get("last_price", 0),
                    row.get("source", "rti"),
                ),
            )


def get_foreign_flow(stock_code: str, days: int = 30) -> list[dict]:
    with get_db() as conn:
        cur = conn.execute(
            """SELECT * FROM foreign_flow
               WHERE stock_code = ?
               ORDER BY trade_date DESC
               LIMIT ?""",
            (stock_code.upper(), days),
        )
        return [dict(row) for row in cur.fetchall()]


def get_accumulation_status(stock_code: str) -> Optional[dict]:
    with get_db() as conn:
        cur = conn.execute(
            """SELECT * FROM foreign_accumulation
               WHERE stock_code = ?
               ORDER BY trade_date DESC
               LIMIT 1""",
            (stock_code.upper(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_accumulation_status() -> list[dict]:
    with get_db() as conn:
        cur = conn.execute(
            """SELECT fa.* FROM foreign_accumulation fa
               INNER JOIN (
                   SELECT stock_code, MAX(trade_date) as max_date
                   FROM foreign_accumulation
                   GROUP BY stock_code
               ) latest ON fa.stock_code = latest.stock_code
               AND fa.trade_date = latest.max_date
               ORDER BY fa.accumulation_days DESC"""
        )
        return [dict(row) for row in cur.fetchall()]


def update_accumulation(stock_code: str, trade_date: str):
    with get_db() as conn:
        cur = conn.execute(
            """SELECT * FROM foreign_flow
               WHERE stock_code = ?
               ORDER BY trade_date DESC
               LIMIT 20""",
            (stock_code.upper(),),
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return

    last_5 = rows[:5]
    last_20 = rows[:20]

    cumulative_net = sum(r.get("foreign_net", 0) for r in last_5)

    accumulation_days = 0
    for r in rows:
        if r.get("foreign_net", 0) > 0:
            accumulation_days += 1
        else:
            break

    distribution_days = 0
    for r in rows:
        if r.get("foreign_net", 0) < 0:
            distribution_days += 1
        else:
            break

    avg_net_5d = sum(r.get("foreign_net", 0) for r in last_5) / len(last_5) if last_5 else 0
    avg_net_20d = sum(r.get("foreign_net", 0) for r in last_20) / len(last_20) if last_20 else 0

    if accumulation_days >= 3:
        status = "accumulating"
    elif distribution_days >= 3:
        status = "distributing"
    else:
        status = "neutral"

    if avg_net_5d > 0 and avg_net_20d > 0:
        strength = "strong"
    elif avg_net_5d > 0 or avg_net_20d > 0:
        strength = "moderate"
    else:
        strength = "weak"

    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO foreign_accumulation
               (stock_code, trade_date, cumulative_net, accumulation_days,
                distribution_days, avg_net_5d, avg_net_20d, status, strength)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                stock_code.upper(),
                trade_date,
                cumulative_net,
                accumulation_days,
                distribution_days,
                avg_net_5d,
                avg_net_20d,
                status,
                strength,
            ),
        )


init_foreign_flow_db()
