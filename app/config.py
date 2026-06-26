import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    NINE_ROUTER_BASE_URL: str = os.getenv("NINE_ROUTER_BASE_URL", "http://localhost:20128/v1")
    NINE_ROUTER_MODEL: str = os.getenv("NINE_ROUTER_MODEL", "test")
    NINE_ROUTER_API_KEY: str = os.getenv("NINE_ROUTER_API_KEY", "***")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "9router")
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "mysql")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:@localhost:3306/analisa_saham")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "")
    CHART_DIR: str = os.getenv("CHART_DIR", "app/static/charts")
    SCHEDULER_INTERVAL: int = int(os.getenv("SCHEDULER_INTERVAL", "15"))
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    MIN_CONFIDENCE_THRESHOLD: int = int(os.getenv("MIN_CONFIDENCE_THRESHOLD", "50"))
    DEFAULT_RISK_LEVEL: str = os.getenv("DEFAULT_RISK_LEVEL", "moderate")
    DEFAULT_STRATEGY: str = os.getenv("DEFAULT_STRATEGY", "swing")
    FOREIGN_FLOW_ENABLED: bool = os.getenv("FOREIGN_FLOW_ENABLED", "true").lower() == "true"
