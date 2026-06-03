import os
import sqlite3
from contextlib import contextmanager
from app.config import Config

DATABASE_DIR = os.path.dirname(Config.DATABASE_PATH)
if DATABASE_DIR:
    os.makedirs(DATABASE_DIR, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, stock_code)
            );

            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                recommendation TEXT,
                confidence REAL,
                trend TEXT,
                rsi REAL,
                macd TEXT,
                price REAL,
                reason TEXT,
                full_analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alert_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stock_code TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT,
                value REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS stock_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT UNIQUE,
                data_json TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS market_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_type TEXT NOT NULL,
                data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                prediction TEXT NOT NULL,
                confidence REAL,
                price_at_prediction REAL,
                price_target REAL,
                strategy TEXT DEFAULT 'swing',
                indicators_used TEXT,
                ai_provider TEXT,
                actual_result TEXT,
                price_after REAL,
                days_to_eval INTEGER DEFAULT 7,
                evaluated INTEGER DEFAULT 0,
                accuracy REAL,
                profit_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                evaluated_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stock_code TEXT,
                prediction_id INTEGER,
                feedback_type TEXT NOT NULL,
                feedback_value TEXT NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (prediction_id) REFERENCES ai_predictions(id)
            );

            CREATE TABLE IF NOT EXISTS ai_user_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                risk_level TEXT DEFAULT 'moderate',
                strategy TEXT DEFAULT 'swing',
                confidence_threshold REAL DEFAULT 60.0,
                auto_learning INTEGER DEFAULT 1,
                ai_provider TEXT DEFAULT 'auto',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS ai_indicator_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 0,
                rsi_weight REAL DEFAULT 1.0,
                macd_weight REAL DEFAULT 1.0,
                volume_weight REAL DEFAULT 1.0,
                trend_weight REAL DEFAULT 1.0,
                sentiment_weight REAL DEFAULT 1.0,
                support_resistance_weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_model_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                score_type TEXT NOT NULL,
                score_value REAL,
                total_predictions INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                winrate REAL,
                avg_profit_pct REAL,
                total_profit_pct REAL,
                period_days INTEGER,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                source TEXT,
                embedding TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL UNIQUE,
                display_name TEXT,
                description TEXT,
                holding_period TEXT,
                risk_profile TEXT,
                indicators_priority TEXT,
                min_confidence REAL DEFAULT 60.0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL UNIQUE,
                prompt_type TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ai_training_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                training_type TEXT NOT NULL,
                model_name TEXT,
                accuracy REAL,
                precision REAL,
                recall REAL,
                f1_score REAL,
                parameters TEXT,
                duration_seconds REAL,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
