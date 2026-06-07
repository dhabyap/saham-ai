"""Shared constants for the entire application.

Centralizes duplicated strings, magic numbers, and configuration
that was previously hardcoded across multiple modules.
"""

import os

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(PROJECT_ROOT, "app", "static")
CHARTS_DIR = os.path.join(STATIC_DIR, "charts")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "app", "templates")
DATABASE_DIR = os.path.join(PROJECT_ROOT, "app", "database")

# ── HTTP ───────────────────────────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
}

# ── Markets / Sectors ──────────────────────────────────────────────────────
SECTOR_MAP = {
    "AALI": "Agriculture",  "ADRO": "Energy",        "AKRA": "Energy",
    "ANTM": "Mining",       "ARTO": "Technology",     "ASII": "Automotive",
    "BBCA": "Financials",   "BBNI": "Financials",     "BBRI": "Financials",
    "BBTN": "Financials",   "BDMN": "Financials",     "BMRI": "Financials",
    "BREN": "Energy",       "BRMS": "Mining",         "CPIN": "Consumer",
    "EMAS": "Technology",   "EXCL": "Infrastructure", "GOTO": "Technology",
    "HRUM": "Mining",       "ICBP": "Consumer",       "INCO": "Mining",
    "INDF": "Consumer",     "INDY": "Energy",         "ITMG": "Energy",
    "JPFA": "Consumer",     "JSMR": "Infrastructure", "KLBF": "Healthcare",
    "MDKA": "Mining",       "MEDC": "Energy",         "MIKA": "Healthcare",
    "PGAS": "Energy",       "PTBA": "Energy",         "SMMA": "Infrastructure",
    "SMGR": "Infrastructure", "TLKM": "Infrastructure", "TOWR": "Infrastructure",
    "TPIA": "Chemicals",    "UNTR": "Energy",         "UNVR": "Consumer",
}

# Technical analysis constants
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MA_SHORT = 20
MA_LONG = 50
VOLUME_SPIKE_THRESHOLD = 1.5
SUPPORT_RESISTANCE_PROXIMITY = 0.02
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
OPENING_RANGE_MINUTES = 30

# Scoring weights
FOREIGN_WEIGHT = 0.35
TECHNICAL_WEIGHT = 0.25
FUNDAMENTAL_WEIGHT = 0.20
SENTIMENT_WEIGHT = 0.20

# Market thresholds
MARKET_FLOW_INFLOW = 0.5
MARKET_FLOW_OUTFLOW = -0.5
FEAR_GREED_STRONG = 2
FEAR_GREED_MODERATE = 15
