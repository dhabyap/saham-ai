import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
    OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "AI Stock Analyzer")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
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
