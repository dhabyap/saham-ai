import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse # Added HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import threading

from app.config import Config
from app.database.database import init_db
from app.api.routes import router
from app.api.learning_routes import router as learning_router
from app.api.upload_routes import router as upload_router
from app.scheduler.scheduler import start_scheduler
from app.constants import STATIC_DIR, CHARTS_DIR, TEMPLATES_DIR, DATABASE_DIR

logger = logging.getLogger(__name__)


app = FastAPI(
    title="AI Stock Analyzer Indonesia",
    description="Analisa saham IDX dengan AI, Telegram Bot, dan Dashboard",
    version="1.0.0",
)

# Mount static files
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Jinja2 templates with custom delimiters to avoid Vue {{ }} conflict
# Vue uses {{ }} for expressions, so Jinja2 must NOT use {{ }}
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.block_start_string = '{%'
templates.env.block_end_string = '%}'
templates.env.variable_start_string = '{$'
templates.env.variable_end_string = '$}'
templates.env.comment_start_string = '{#'
templates.env.comment_end_string = '#}'

# Include API routes
app.include_router(router)
app.include_router(learning_router)
app.include_router(upload_router)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    logger.info("✓ Database initialized")

    from app.database import foreign_flow_models
    logger.info("✓ Foreign flow database initialized")

    # Seed knowledge base
    try:
        from app.ai.knowledge_base import seed_knowledge_base
        seed_knowledge_base()
        logger.info("✓ Knowledge base seeded")
    except Exception as e:
        logger.warning("⚠ Knowledge base seed: %s", e)

    # Seed default prompts
    try:
        _seed_default_prompts()
    except Exception as e:
        logger.warning("⚠ Prompt seed: %s", e)

    # Seed default strategies
    try:
        _seed_default_strategies()
    except Exception as e:
        logger.warning("⚠ Strategy seed: %s", e)

    # Initialize shareholder table
    try:
        from app.services.shareholder_service import get_latest_period
        get_latest_period()
        logger.info("✓ Shareholder database initialized")
    except Exception as e:
        logger.warning("⚠ Shareholder table: %s", e)

    # Start scheduler
    start_scheduler()

    # Start Telegram bot in a separate thread
    _start_telegram_bot()


def _start_telegram_bot() -> None:
    try:
        from app.telegram.bot import TelegramBot

        bot = TelegramBot()
        if bot.token:
            thread = threading.Thread(target=bot.run, daemon=True)
            thread.start()
            logger.info("✓ Telegram Bot thread started")
        else:
            logger.warning("⚠ Telegram Bot disabled (no token)")
    except Exception as e:
        logger.warning("⚠ Telegram Bot error: %s", e)


@app.get("/")
async def root(request: Request):
    """Vue 3 dashboard SPA"""
    return templates.TemplateResponse(
        "dashboard_vue.html",
        {"request": request},
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@app.get("/dashboard")
async def dashboard_vue(request: Request):
    """Vue 3 dashboard with 3 themes"""
    return templates.TemplateResponse("dashboard_vue.html", {"request": request})


@app.get("/market-reports")
async def market_reports_page(request: Request):
    """Market reports page - serves SPA with market view active"""
    return templates.TemplateResponse("dashboard_vue.html", {"request": request})


@app.get("/shareholders")
async def shareholders_page(request: Request):
    """Shareholder >1% tracking page"""
    return templates.TemplateResponse("dashboard_vue.html", {"request": request})


@app.get("/api-docs")
async def api_docs():
    return {
        "swagger": "/docs",
        "redoc": "/redoc",
        "ai_settings": "/ai-settings",
        "ai_performance": "/ai-performance",
        "endpoints": {
            "GET /api/health": "Health check",
            "GET /api/stocks": "List all stocks",
            "GET /api/stock/{code}": "Get stock data",
            "GET /api/analyze/{code}": "Analyze stock with AI",
            "GET /api/chart/{code}": "Generate stock chart",
            "GET /api/market-summary": "Market overview",
            "GET /api/market-sentiment": "Market sentiment",
            "GET /api/sector-performance": "Sector performance",
            "GET /api/top-gainers": "Top gainers",
            "GET /api/top-losers": "Top losers",
            "GET /api/top-volume": "Top volume",
            "GET /api/watchlist/{user_id}": "Get user watchlist",
            "GET /api/analysis-history": "Analysis history",
            "GET /api/alerts": "Alert logs",
            "POST /api/watchlist/add": "Add to watchlist",
            "POST /api/watchlist/remove": "Remove from watchlist",
            "GET /api/learning/performance": "AI Learning performance",
            "GET /api/learning/config/{user_id}": "AI user config",
            "GET /api/learning/weights/{user_id}": "Indicator weights",
            "POST /api/learning/feedback": "Submit feedback",
            "POST /api/learning/train": "Train ML model",
            "GET /api/learning/backtest/{code}": "Backtest strategy",
            "GET /ai-settings": "AI Settings dashboard",
            "GET /ai-performance": "AI Performance dashboard",
        },
    }


def _seed_default_prompts():
    prompts = {
        "custom_analyst": {
            "type": "analyst",
            "text": "Anda adalah analis saham profesional untuk pasar Indonesia (IDX). "
                    "Analisis data saham dan berikan rekomendasi BUY, HOLD, atau SELL. "
                    "Output dalam format JSON.",
        },
        "custom_risk": {
            "type": "risk",
            "text": "Anda adalah analis risiko saham. Evaluasi tingkat risiko berdasarkan data teknikal. Output JSON.",
        },
        "custom_sentiment": {
            "type": "sentiment",
            "text": "Anda adalah analis sentimen pasar. Analisis data market dan berikan output JSON.",
        },
    }
    from app.database import ai_crud
    for name, data in prompts.items():
        existing = ai_crud.get_prompt(name)
        if not existing:
            ai_crud.save_prompt(name, data["type"], data["text"], is_default=1)


def _seed_default_strategies():
    strategies = [
        {"name": "scalping", "display": "Scalping", "desc": "Trading jangka pendek (detik-menit), target 0.1-0.5%",
         "period": "intraday", "risk": "high", "indicators": ["volume", "rsi", "trend"], "confidence": 50},
        {"name": "swing", "display": "Swing Trade", "desc": "Trading jangka menengah (hari-minggu), target 5-15%",
         "period": "days", "risk": "moderate", "indicators": ["rsi", "macd", "trend", "volume"], "confidence": 60},
        {"name": "long_term", "display": "Long Term", "desc": "Investasi jangka panjang (bulan-tahun), fokus fundamental",
         "period": "months", "risk": "low", "indicators": ["trend", "support_resistance"], "confidence": 65},
        {"name": "dividend", "display": "Dividend", "desc": "Fokus pada saham dividen tinggi dan stabil",
         "period": "months", "risk": "low", "indicators": ["trend", "support_resistance"], "confidence": 60},
    ]
    from app.database import ai_crud
    for s in strategies:
        existing = ai_crud.get_strategy(s["name"])
        if not existing:
            ai_crud.save_strategy(
                s["name"], s["display"], s["desc"],
                s["period"], s["risk"], s["indicators"], s["confidence"],
            )