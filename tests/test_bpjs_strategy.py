import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np

from app.services.stock_service import get_opening_range
from app.ai.strategies.bpjs_strategy import BPJSStrategy


def _make_intraday_df(close_values: list, high_offset: float = 5, low_offset: float = 5, volume: int = 1_000_000):
    n = len(close_values)
    opens = [close_values[0]] + close_values[:-1]
    data = {
        "Open": opens,
        "High": [c + high_offset for c in close_values],
        "Low": [c - low_offset for c in close_values],
        "Close": close_values,
        "Volume": [volume] * n,
    }
    idx = pd.date_range("2026-06-05 09:00", periods=n, freq="5min")
    df = pd.DataFrame(data, index=idx)
    df.index.name = "Date"
    return df


def _make_uptrend_df():
    base = 10000
    values = [base + i * 50 for i in range(60)]
    n = len(values)
    opens = [values[0]] + values[:-1]
    volumes = [5_000_000] * 6 + [1_000_000] * (n - 6)
    data = {
        "Open": opens,
        "High": [v + 20 for v in values],
        "Low": [v - 10 for v in values],
        "Close": values,
        "Volume": volumes,
    }
    idx = pd.date_range("2026-06-05 09:00", periods=n, freq="5min")
    df = pd.DataFrame(data, index=idx)
    df.index.name = "Date"
    return df


def test_get_opening_range():
    df = _make_uptrend_df()
    result = get_opening_range(df, interval="5m")
    assert isinstance(result, dict)
    assert "open_range_high" in result
    assert "open_range_low" in result
    assert "range_pct" in result
    assert result["open_range_high"] > result["open_range_low"]
    assert result["range_pct"] > 0


def test_get_entry_signal_breakout():
    df = _make_uptrend_df()
    strategy = BPJSStrategy()
    signal = strategy.get_entry_signal("BBCA", df)
    assert signal["action"] == "ENTER"


def test_get_exit_signal():
    strategy = BPJSStrategy()
    entry_price = 10000.0
    target = entry_price * 1.015
    cut_loss = entry_price * 0.993

    tp = strategy.get_exit_signal(entry_price, target, cut_loss, target + 10, "10:00")
    assert tp["action"] == "EXIT_TP"

    cl = strategy.get_exit_signal(entry_price, target, cut_loss, cut_loss - 10, "10:00")
    assert cl["action"] == "EXIT_CL"

    hold = strategy.get_exit_signal(entry_price, target, cut_loss, entry_price + 50, "12:00")
    assert hold["action"] == "HOLD"

    time_exit = strategy.get_exit_signal(entry_price, target, cut_loss, entry_price + 50, "14:45")
    assert time_exit["action"] == "EXIT_TIME"
