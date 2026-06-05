import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from app.services.ihsg_service import IHSGService
from app.services.relative_strength import calculate_relative_strength


def test_fetch_ihsg_data():
    df = IHSGService().fetch_ihsg_data(period="5d")
    assert df is not None, "fetch_ihsg_data returned None"
    assert isinstance(df, pd.DataFrame), "result is not a DataFrame"
    expected_columns = {"Open", "High", "Low", "Close", "Volume"}
    assert expected_columns.issubset(set(df.columns)), f"Missing columns. Got: {list(df.columns)}"
    assert len(df) > 0, "DataFrame is empty"


def test_get_ihsg_summary():
    result = IHSGService().get_ihsg_summary()
    assert result is not None, "get_ihsg_summary returned None"
    expected_keys = {
        "current_price", "change_pct", "weekly_change", "monthly_change",
        "ytd_change", "ma20", "ma50", "trend", "support", "resistance",
        "volume_trend", "last_updated",
    }
    assert expected_keys.issubset(set(result.keys())), f"Missing keys. Got: {list(result.keys())}"


def test_calculate_relative_strength():
    result = calculate_relative_strength("BBCA")
    assert result is not None, "calculate_relative_strength returned None"
    expected_keys = {
        "stock_code", "stock_return_pct", "ihsg_return_pct",
        "rs_value", "rs_status", "period_days", "last_updated",
    }
    assert expected_keys.issubset(set(result.keys())), f"Missing keys. Got: {list(result.keys())}"
    assert isinstance(result["rs_value"], (int, float)), "rs_value should be numeric"
