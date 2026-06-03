import json
from datetime import datetime, timedelta
from app.database.database import get_db


def add_user(telegram_id, username=None):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username),
        )
        cur = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        return dict(cur.fetchone())


def get_user(telegram_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def add_to_watchlist(user_id, stock_code, stock_name=None):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, stock_code, stock_name) VALUES (?, ?, ?)",
            (user_id, stock_code.upper(), stock_name),
        )


def remove_from_watchlist(user_id, stock_code):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND stock_code = ?",
            (user_id, stock_code.upper()),
        )


def get_watchlist(user_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_all_watchlist_codes():
    with get_db() as conn:
        cur = conn.execute("SELECT DISTINCT stock_code FROM watchlist")
        return [row["stock_code"] for row in cur.fetchall()]


def save_analysis(stock_code, stock_name, recommendation, confidence, trend, rsi, macd, price, reason, full_analysis):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO analysis_history
            (stock_code, stock_name, recommendation, confidence, trend, rsi, macd, price, reason, full_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (stock_code, stock_name, recommendation, confidence, trend, rsi, macd, price, reason, full_analysis),
        )


def get_recent_analysis(limit=20):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def save_alert(user_id, stock_code, alert_type, message, value=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO alert_logs (user_id, stock_code, alert_type, message, value) VALUES (?, ?, ?, ?, ?)",
            (user_id, stock_code, alert_type, message, value),
        )


def get_alerts(limit=20):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM alert_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def cache_stock_data(stock_code, data_json):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM stock_cache WHERE stock_code = ?", (stock_code.upper(),)
        ).fetchone()
        data_str = json.dumps(data_json, default=str)
        if existing:
            conn.execute(
                "UPDATE stock_cache SET data_json = ?, last_updated = CURRENT_TIMESTAMP WHERE stock_code = ?",
                (data_str, stock_code.upper()),
            )
        else:
            conn.execute(
                "INSERT INTO stock_cache (stock_code, data_json) VALUES (?, ?)",
                (stock_code.upper(), data_str),
            )


def get_cached_stock(stock_code, max_age_minutes=5):
    with get_db() as conn:
        cutoff = (datetime.now() - timedelta(minutes=max_age_minutes)).isoformat()
        cur = conn.execute(
            "SELECT * FROM stock_cache WHERE stock_code = ? AND last_updated > ?",
            (stock_code.upper(), cutoff),
        )
        row = cur.fetchone()
        if row:
            return json.loads(row["data_json"])
        return None


def save_market_summary(summary_type, data_json):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO market_summary (summary_type, data_json) VALUES (?, ?)",
            (summary_type, json.dumps(data_json, default=str)),
        )


def get_latest_market_summary(summary_type):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM market_summary WHERE summary_type = ? ORDER BY created_at DESC LIMIT 1",
            (summary_type,),
        )
        row = cur.fetchone()
        if row:
            return json.loads(row["data_json"])
        return None


def get_all_users():
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM users WHERE is_active = 1")
        return [dict(row) for row in cur.fetchall()]


def get_telegram_ids():
    with get_db() as conn:
        cur = conn.execute("SELECT telegram_id FROM users WHERE is_active = 1 AND telegram_id IS NOT NULL")
        return [row["telegram_id"] for row in cur.fetchall()]
