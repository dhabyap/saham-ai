import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from app.database.database import get_db
from app.database.foreign_flow_models import (
    init_foreign_flow_db,
    save_foreign_flow,
    get_foreign_flow,
    update_accumulation,
    get_accumulation_status,
)
from app.services.foreign_flow_service import estimate_foreign_flow_from_price


def test_init_tables():
    init_foreign_flow_db()
    with get_db() as conn:
        from app.database.database import DB_TYPE
        if DB_TYPE == "mysql":
            cur = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name IN ('foreign_flow', 'foreign_accumulation')"
            )
        else:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('foreign_flow', 'foreign_accumulation')"
            )
        tables = {list(row.values())[0] for row in cur.fetchall()}
    assert "foreign_flow" in tables
    assert "foreign_accumulation" in tables


def test_save_and_get_foreign_flow():
    init_foreign_flow_db()
    data = [
        {
            "stock_code": "TEST",
            "trade_date": "2026-06-01",
            "foreign_buy": 100000000000,
            "foreign_sell": 50000000000,
            "foreign_net": 50000000000,
            "source": "rti",
        },
        {
            "stock_code": "TEST",
            "trade_date": "2026-06-02",
            "foreign_buy": 200000000000,
            "foreign_sell": 100000000000,
            "foreign_net": 100000000000,
            "source": "rti",
        },
    ]
    save_foreign_flow(data)
    rows = get_foreign_flow("TEST", days=10)
    assert len(rows) >= 2
    assert rows[0]["stock_code"] == "TEST"
    assert rows[0]["foreign_net"] == 100000000000


def test_update_accumulation():
    init_foreign_flow_db()
    base_data = []
    for i in range(5):
        day = f"2026-05-{28 + i:02d}"
        net = 50000000000 + (i * 10000000000)
        base_data.append({
            "stock_code": "ACCUM",
            "trade_date": day,
            "foreign_buy": net + 10000000000,
            "foreign_sell": 10000000000,
            "foreign_net": net,
            "source": "rti",
        })
    save_foreign_flow(base_data)
    update_accumulation("ACCUM", "2026-06-01")
    status = get_accumulation_status("ACCUM")
    assert status is not None
    assert status["status"] == "accumulating"
    assert status["accumulation_days"] == 5


def test_estimate_foreign_flow():
    data = {
        "Open": [1000, 1010, 1020, 1030, 1040],
        "High": [1020, 1030, 1040, 1050, 1060],
        "Low": [990, 1000, 1010, 1020, 1030],
        "Close": [1010, 1020, 1030, 1040, 1050],
        "Volume": [1000000, 2000000, 3000000, 4000000, 5000000],
    }
    df = pd.DataFrame(data)
    result = estimate_foreign_flow_from_price(df, "BBCA")
    assert result is not None
    assert result["stock_code"] == "BBCA"
    assert result["source"] == "estimated"
    assert "confidence" in result
    assert result["foreign_buy"] >= 0
    assert result["foreign_sell"] >= 0
