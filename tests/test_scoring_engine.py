import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ai.scoring_engine import ScoringEngine, ScoringComponent


def test_scoring_components_have_weights():
    engine = ScoringEngine()
    result = engine.calculate_score("BBCA")
    assert len(result.components) == 6
    component_names = {c.name for c in result.components}
    expected = {"Technical", "Foreign Flow", "Accumulation", "Relative Strength", "Sector", "Sentiment"}
    assert component_names == expected
    total_weight = sum(c.weight for c in result.components)
    assert abs(total_weight - 1.0) < 0.01


def test_scoring_returns_valid_result():
    engine = ScoringEngine()
    result = engine.calculate_score("BBCA")
    assert result.recommendation in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
    assert 0 <= result.total_score <= 100
    assert 1 <= result.confidence <= 99
    assert result.stock_code == "BBCA"


def test_day_trade_strategy_weights():
    engine = ScoringEngine()
    result = engine.calculate_score("BBCA", strategy="day_trade")
    for c in result.components:
        if c.name == "Technical":
            assert abs(c.weight - 0.20) < 0.01
            break


def test_long_term_strategy_weights():
    engine = ScoringEngine()
    result = engine.calculate_score("BBCA", strategy="long_term")
    for c in result.components:
        if c.name == "Accumulation":
            assert abs(c.weight - 0.50) < 0.01
            break


def test_sector_scoring():
    engine = ScoringEngine()
    component = engine.score_sector("BBCA")
    assert component.name == "Sector"
    assert isinstance(component, ScoringComponent)
