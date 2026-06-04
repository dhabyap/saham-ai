import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    NINE_ROUTER_BASE_URL = os.getenv("NINE_ROUTER_BASE_URL", "http://localhost:20128/v1")
    NINE_ROUTER_MODEL = os.getenv("NINE_ROUTER_MODEL", "test")
    NINE_ROUTER_API_KEY = os.getenv("NINE_ROUTER_API_KEY", "sk-9router-free")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "9router")
    DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app/database/stock.db")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "app/database/stock.db")
    CHART_DIR = os.getenv("CHART_DIR", "app/static/charts")
    SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "15"))
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    MIN_CONFIDENCE_THRESHOLD = int(os.getenv("MIN_CONFIDENCE_THRESHOLD", "50"))
    DEFAULT_RISK_LEVEL = os.getenv("DEFAULT_RISK_LEVEL", "moderate")
    DEFAULT_STRATEGY = os.getenv("DEFAULT_STRATEGY", "swing")
