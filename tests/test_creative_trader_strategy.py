import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ai.strategies.creative_trader_strategy import CreativeTraderStrategy


def test_analyze_accumulation():
    strategy = CreativeTraderStrategy()
    result = strategy.analyze_accumulation_phase("BBCA")
    if result is None:
        return
    expected_keys = {
        "stock_code", "phase", "accumulation_days", "distribution_days",
        "cumulative_net_20d", "net_buy_ratio", "supply_absorbed",
        "hidden_accumulation", "price_range_20d", "volume_trend",
        "avg_entry_zone", "current_price", "confidence",
    }
    assert expected_keys.issubset(set(result.keys())), f"Missing keys. Got: {list(result.keys())}"
    assert result["phase"] in (
        "active_accumulation", "early_accumulation",
        "heavy_distribution", "early_distribution", "neutral",
    ), f"Unexpected phase: {result['phase']}"
    assert "upper" in result["avg_entry_zone"]
    assert "lower" in result["avg_entry_zone"]
    assert "current_position" in result["avg_entry_zone"]
    assert isinstance(result["confidence"], (int, float))
    assert 0 <= result["confidence"] <= 100


def test_calculate_entry_point():
    strategy = CreativeTraderStrategy()
    result = strategy.calculate_entry_point("BBCA")
    assert result is not None, "calculate_entry_point returned None"
    assert "action" in result, "Missing action key"
    assert result["action"] in ("BUY", "ACCUMULATE", "WAIT"), f"Unexpected action: {result['action']}"
    assert "entry_type" in result
    assert "entry_price" in result
    assert "suggested_range" in result
    assert "stop_loss" in result
    assert "target_profit" in result
    assert "short_term" in result["target_profit"]
    assert "medium_term" in result["target_profit"]
    assert "reason" in result


def test_multi_timeframe():
    strategy = CreativeTraderStrategy()
    result = strategy.multi_timeframe_analysis("BBCA")
    assert result is not None, "multi_timeframe_analysis returned None"
    expected_keys = {"weekly_outlook", "daily_phase", "intraday_momentum", "alignment"}
    assert expected_keys.issubset(set(result.keys())), f"Missing keys. Got: {list(result.keys())}"
    assert result["alignment"] in ("ALIGNED", "WARNING", "CONFLICT"), f"Unexpected alignment: {result['alignment']}"


def test_scan_candidates():
    strategy = CreativeTraderStrategy()
    result = strategy.scan_for_long_term_candidates(["BBCA"])
    assert isinstance(result, list), "scan_for_long_term_candidates did not return a list"
