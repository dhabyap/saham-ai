"""Tests for the Vue 3 dashboard route."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_returns_200() -> None:
    """GET /dashboard should return 200 OK."""
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_dashboard_includes_title() -> None:
    """Response HTML should contain 'AI Stock Analyzer'."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "AI Stock Analyzer" in response.text


def test_dashboard_uses_vue3() -> None:
    """Response should include Vue 3 script tag."""
    response = client.get("/dashboard")
    assert "vue@3" in response.text or "vue.global" in response.text


def test_dashboard_has_three_themes() -> None:
    """Response should contain all 3 theme buttons."""
    response = client.get("/dashboard")
    html = response.text
    assert "neumorphism" in html
    assert "dark" in html
    assert "classy" in html


def test_dashboard_has_market_summary() -> None:
    """Response should contain market summary section."""
    response = client.get("/dashboard")
    assert "Market Summary" in response.text


def test_dashboard_has_predictions_table() -> None:
    """Response should contain recent predictions table."""
    response = client.get("/dashboard")
    assert "Recent Predictions" in response.text
