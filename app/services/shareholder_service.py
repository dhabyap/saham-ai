"""Shareholder >1% data service."""
from typing import Optional
from app.database.database import get_db
from app.config import Config


_SHAREHOLDER_TABLE_INITED = False


def _mysql_sql():
    return """
        CREATE TABLE IF NOT EXISTS shareholders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(20) NOT NULL,
            shareholder_name VARCHAR(255) NOT NULL,
            share_count BIGINT DEFAULT 0,
            share_percent DECIMAL(10,4) DEFAULT 0,
            category VARCHAR(50) DEFAULT NULL,
            data_period VARCHAR(10) NOT NULL,
            source VARCHAR(50) DEFAULT 'idx',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_holder (stock_code, shareholder_name, data_period)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """


def _sqlite_sql():
    return """
        CREATE TABLE IF NOT EXISTS shareholders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            shareholder_name TEXT NOT NULL,
            share_count INTEGER DEFAULT 0,
            share_percent REAL DEFAULT 0,
            category TEXT DEFAULT '',
            data_period TEXT NOT NULL,
            source TEXT DEFAULT 'idx',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            UNIQUE(stock_code, shareholder_name, data_period)
        )
    """


def _ensure_table():
    global _SHAREHOLDER_TABLE_INITED
    if _SHAREHOLDER_TABLE_INITED:
        return

    # Detect DB type from DATABASE_URL in config
    db_url = Config.DATABASE_URL or ''
    is_sqlite = 'sqlite' in db_url.lower()

    sql = _sqlite_sql() if is_sqlite else _mysql_sql()
    with get_db() as conn:
        conn.executescript(sql)
    _SHAREHOLDER_TABLE_INITED = True


def get_shareholders_by_stock(stock_code: str, period: Optional[str] = None) -> list[dict]:
    """Get shareholder data for a stock code."""
    _ensure_table()
    with get_db() as conn:
        if period:
            rows = conn.execute(
                "SELECT * FROM shareholders WHERE stock_code = ? AND data_period = ? ORDER BY share_percent DESC",
                (stock_code.upper(), period)
            )
        else:
            rows = conn.execute(
                "SELECT * FROM shareholders WHERE stock_code = ? ORDER BY data_period DESC, share_percent DESC",
                (stock_code.upper(),)
            )
        return [dict(r) for r in rows]


def get_shareholder_portfolio(shareholder_name: str, period: Optional[str] = None) -> list[dict]:
    """Get all stocks held by a specific shareholder."""
    _ensure_table()
    with get_db() as conn:
        if period:
            rows = conn.execute(
                "SELECT * FROM shareholders WHERE shareholder_name LIKE ? AND data_period = ? ORDER BY share_percent DESC",
                (f'%{shareholder_name.upper()}%', period)
            )
        else:
            rows = conn.execute(
                "SELECT * FROM shareholders WHERE shareholder_name LIKE ? ORDER BY data_period DESC, share_percent DESC",
                (f'%{shareholder_name.upper()}%',)
            )
        return [dict(r) for r in rows]


def get_available_periods() -> list[str]:
    """Get list of available data periods."""
    _ensure_table()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT data_period FROM shareholders ORDER BY data_period DESC"
        )
        return [r['data_period'] for r in rows]


def get_top_shareholders(
    limit: int = 20,
    period: Optional[str] = None,
    min_pct: float = 1.0
) -> list[dict]:
    """Get top individual shareholders across all stocks."""
    _ensure_table()
    with get_db() as conn:
        if period:
            rows = conn.execute(
                """SELECT shareholder_name, COUNT(*) as stock_count,
                          SUM(share_percent) as total_pct
                   FROM shareholders
                   WHERE data_period = ? AND share_percent >= ?
                   GROUP BY shareholder_name
                   ORDER BY stock_count DESC, total_pct DESC
                   LIMIT ?""",
                (period, min_pct, limit)
            )
        else:
            rows = conn.execute(
                """SELECT shareholder_name, COUNT(*) as stock_count,
                          SUM(share_percent) as total_pct
                   FROM shareholders
                   WHERE share_percent >= ?
                   GROUP BY shareholder_name
                   ORDER BY stock_count DESC, total_pct DESC
                   LIMIT ?""",
                (min_pct, limit)
            )
        return [dict(r) for r in rows]


def upsert_shareholder(
    stock_code: str,
    shareholder_name: str,
    share_percent: float,
    share_count: int = 0,
    category: str = '',
    data_period: str = '',
    source: str = 'manual',
) -> dict:
    """Insert or update a shareholder record. Returns {'action': 'inserted'|'updated'}."""
    _ensure_table()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM shareholders WHERE stock_code = ? AND shareholder_name = ? AND data_period = ?",
            (stock_code.upper(), shareholder_name.upper(), data_period)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE shareholders SET share_count=?, share_percent=?, category=?, source=?, updated_at=datetime('now')
                   WHERE stock_code=? AND shareholder_name=? AND data_period=?""",
                (share_count, share_percent, category, source, stock_code.upper(), shareholder_name.upper(), data_period)
            )
            return {'action': 'updated'}
        else:
            conn.execute(
                """INSERT INTO shareholders (stock_code, shareholder_name, share_count, share_percent, category, data_period, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (stock_code.upper(), shareholder_name.upper(), share_count, share_percent, category, data_period, source)
            )
            return {'action': 'inserted'}


def period_has_data(data_period: str) -> bool:
    """Check if period already has any records."""
    _ensure_table()
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM shareholders WHERE data_period = ? LIMIT 1",
            (data_period,)
        ).fetchone()
        return row is not None


def bulk_import(data: list[dict], data_period: str) -> dict:
    """Bulk import shareholder data. Returns summary."""
    _ensure_table()
    inserted = 0
    updated = 0
    errors = []
    for i, item in enumerate(data):
        try:
            stock_code = item.get('stock_code', '').strip()
            name = item.get('shareholder_name', '').strip()
            pct = float(item.get('share_percent', 0))
            count = int(item.get('share_count', 0))
            cat = item.get('category', '')
            if not stock_code or not name:
                errors.append(f"Row {i}: missing stock_code or shareholder_name")
                continue
            result = upsert_shareholder(stock_code, name, pct, count, cat, data_period, 'manual')
            if result.get('action') == 'inserted':
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")
    return {"imported": inserted, "updated": updated, "errors": errors, "total": len(data)}


def get_latest_period() -> Optional[str]:
    """Get the latest available data period."""
    _ensure_table()
    with get_db() as conn:
        row = conn.execute(
            "SELECT data_period FROM shareholders ORDER BY data_period DESC LIMIT 1"
        ).fetchone()
        return row['data_period'] if row else None


def get_shareholder_graph_data(period: Optional[str] = None, min_pct: float = 5.0) -> dict:
    """
    Get shareholder data for graph visualization (nodes and edges).
    Matches format expected by renderForceGraph() in charts.js.
    min_pct: minimum share_percent threshold to include (default 5%).
    """
    _ensure_table()
    nodes = []
    edges = []
    
    with get_db() as conn:
        if period:
            rows = conn.execute(
                """SELECT stock_code, shareholder_name, share_percent
                   FROM shareholders
                   WHERE data_period = ? AND share_percent >= ?
                   ORDER BY stock_code, shareholder_name""",
                (period, min_pct)
            )
        else:
            rows = conn.execute(
                """SELECT stock_code, shareholder_name, share_percent, data_period
                   FROM shareholders
                   WHERE share_percent >= ?
                   ORDER BY data_period DESC, stock_code, shareholder_name""",
                (min_pct,)
            )
        
        stock_nodes = set()
        shareholder_nodes: dict[str, dict] = {}

        for r in rows:
            record = dict(r)
            stock_code = record['stock_code']
            shareholder_name = record['shareholder_name']
            share_percent = float(record['share_percent'])

            if stock_code not in stock_nodes:
                nodes.append({
                    "id": stock_code,
                    "label": stock_code,
                    "type": "stock",
                    "size": 12,
                })
                stock_nodes.add(stock_code)
            
            if shareholder_name not in shareholder_nodes:
                shareholder_nodes[shareholder_name] = {
                    "id": shareholder_name,
                    "label": shareholder_name,
                    "type": "shareholder",
                    "size": 0,
                    "total_pct": 0.0,
                    "stock_count": 0,
                }
            
            sh = shareholder_nodes[shareholder_name]
            sh["size"] += share_percent
            sh["total_pct"] = round(sh["total_pct"] + share_percent, 2)
            sh["stock_count"] += 1
            
            edges.append({
                "from": shareholder_name,
                "to": stock_code,
                "value": share_percent,
                "title": f"{shareholder_name} owns {share_percent:.2f}% of {stock_code}",
            })
    
    # Add computed shareholder nodes
    for sh in shareholder_nodes.values():
        nodes.append(sh)
            
    return {"nodes": nodes, "edges": edges}
