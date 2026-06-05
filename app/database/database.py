import os
import sqlite3
from contextlib import contextmanager
from app.config import Config

DATABASE_DIR = os.path.dirname(Config.DATABASE_PATH)
if DATABASE_DIR:
    os.makedirs(DATABASE_DIR, exist_ok=True)

# Detect database type from config
DB_TYPE = getattr(Config, "DATABASE_TYPE", "sqlite").lower()

def _get_mysql_connection():
    """Get MySQL connection using mysql-connector-python."""
    import mysql.connector
    url = Config.DATABASE_URL
    # Parse: mysql+mysqlconnector://user:pass@host:port/dbname
    parts = url.replace("mysql+mysqlconnector://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host = host_port_db[0].split(":")[0]
    port = int(host_port_db[0].split(":")[1]) if ":" in host_port_db[0] else 3306
    dbname = host_port_db[1]
    conn = mysql.connector.connect(
        host=host, port=port, user=user, password=password, database=dbname,
        autocommit=False
    )
    return conn

class MySQLRow(dict):
    """Dict that also supports integer indexing, like sqlite3.Row."""
    def __getitem__(self, key):
        if isinstance(key, int):
            keys = list(self.keys())
            if 0 <= key < len(keys):
                return super().__getitem__(keys[key])
            raise IndexError(key)
        return super().__getitem__(key)

class MySQLCursorWrapper:
    """Wrap MySQL cursor to provide sqlite3.Row-like interface."""
    def __init__(self, cursor, connection=None):
        self._cursor = cursor
        self._connection = connection
        self.description = cursor.description

    def cursor(self):
        """Return self as cursor (compatibility with connection.cursor() pattern)."""
        return self

    def commit(self):
        """Commit the underlying connection."""
        if self._connection:
            self._connection.commit()

    def rollback(self):
        """Rollback the underlying connection."""
        if self._connection:
            self._connection.rollback()

    def _row_to_dict(self, row):
        if row is None:
            return None
        cols = [d[0] for d in self.description] if self.description else []
        return MySQLRow(zip(cols, row))

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._row_to_dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def execute(self, query, params=None):
        # Convert SQLite syntax to MySQL syntax
        if DB_TYPE == "mysql":
            if params:
                query = query.replace("?", "%s")
            query = query.replace("INSERT OR IGNORE", "INSERT IGNORE")
            query = query.replace("INSERT OR REPLACE", "REPLACE")
            query = query.replace("last_insert_rowid()", "LAST_INSERT_ID()")
        self._cursor.execute(query, params or ())
        self.description = self._cursor.description
        return self

    def executescript(self, script):
        """For MySQL, split by semicolons and execute each."""
        if DB_TYPE == "mysql":
            for stmt in script.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        self._cursor.execute(stmt)
                    except Exception:
                        pass
        else:
            self._cursor.executescript(script)

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def __iter__(self):
        return self

    def __next__(self):
        row = self._cursor.fetchone()
        if row is None:
            raise StopIteration
        return dict(zip([d[0] for d in self.description], row))

class SQLiteCursorWrapper:
    """Wrap sqlite3 cursor for consistency."""
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def execute(self, query, params=None):
        self._cursor.execute(query, params or ())
        return self

    def executescript(self, script):
        self._cursor.executescript(script)

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description

    def __iter__(self):
        return self._cursor

    def __next__(self):
        return next(self._cursor)

def get_connection():
    if DB_TYPE == "mysql":
        conn = _get_mysql_connection()
        cursor = conn.cursor()
        return conn, MySQLCursorWrapper(cursor)
    else:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn, SQLiteCursorWrapper(conn.cursor())

@contextmanager
def get_db():
    if DB_TYPE == "mysql":
        conn = _get_mysql_connection()
        cursor = conn.cursor()
        wrapped = MySQLCursorWrapper(cursor, connection=conn)
        try:
            yield wrapped
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def _mysql_type(col_type):
    """Map SQLite types to MySQL types."""
    mapping = {
        "INTEGER PRIMARY KEY AUTOINCREMENT": "INT AUTO_INCREMENT PRIMARY KEY",
        "TEXT": "TEXT",
        "REAL": "DOUBLE",
        "TIMESTAMP DEFAULT CURRENT_TIMESTAMP": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "BOOLEAN DEFAULT 0": "TINYINT(1) DEFAULT 0",
        "BOOLEAN DEFAULT 1": "TINYINT(1) DEFAULT 1",
    }
    result = col_type
    for old, new in mapping.items():
        result = result.replace(old, new)
    return result

def init_db():
    with get_db() as conn:
        if DB_TYPE == "mysql":
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    telegram_id INT UNIQUE,
                    username VARCHAR(255),
                    is_active TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    stock_code VARCHAR(50) NOT NULL,
                    stock_name VARCHAR(255),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, stock_code)
                );
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(50) NOT NULL,
                    stock_name VARCHAR(255),
                    recommendation VARCHAR(10),
                    confidence DOUBLE,
                    trend VARCHAR(50),
                    rsi DOUBLE,
                    macd VARCHAR(50),
                    price DOUBLE,
                    reason TEXT,
                    full_analysis TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS alert_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    stock_code VARCHAR(50) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    message TEXT,
                    value DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS stock_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(50) UNIQUE,
                    data_json TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS market_summary (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    summary_type VARCHAR(50) NOT NULL,
                    data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(50) NOT NULL,
                    stock_name VARCHAR(255),
                    prediction VARCHAR(10) NOT NULL,
                    confidence DOUBLE,
                    price_at_prediction DOUBLE,
                    price_target DOUBLE,
                    strategy VARCHAR(50) DEFAULT 'swing',
                    indicators_used TEXT,
                    ai_provider VARCHAR(50),
                    actual_result VARCHAR(10),
                    price_after DOUBLE,
                    days_to_eval INT DEFAULT 7,
                    evaluated TINYINT(1) DEFAULT 0,
                    accuracy DOUBLE,
                    profit_pct DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    evaluated_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_feedback (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    stock_code VARCHAR(50),
                    prediction_id INT,
                    feedback_type VARCHAR(50) NOT NULL,
                    feedback_value VARCHAR(50) NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (prediction_id) REFERENCES ai_predictions(id)
                );
                CREATE TABLE IF NOT EXISTS ai_user_configs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT UNIQUE,
                    risk_level VARCHAR(50) DEFAULT 'moderate',
                    strategy VARCHAR(50) DEFAULT 'swing',
                    confidence_threshold DOUBLE DEFAULT 60.0,
                    auto_learning TINYINT(1) DEFAULT 1,
                    ai_provider VARCHAR(50) DEFAULT 'auto',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS ai_indicator_weights (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT DEFAULT 0,
                    rsi_weight DOUBLE DEFAULT 1.0,
                    macd_weight DOUBLE DEFAULT 1.0,
                    volume_weight DOUBLE DEFAULT 1.0,
                    trend_weight DOUBLE DEFAULT 1.0,
                    sentiment_weight DOUBLE DEFAULT 1.0,
                    support_resistance_weight DOUBLE DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_model_scores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    strategy VARCHAR(50),
                    score_type VARCHAR(50),
                    score_value DOUBLE DEFAULT 0,
                    total_predictions INT DEFAULT 0,
                    correct_predictions INT DEFAULT 0,
                    accuracy DOUBLE DEFAULT 0.0,
                    winrate DOUBLE DEFAULT 0,
                    avg_profit_pct DOUBLE DEFAULT 0,
                    total_profit_pct DOUBLE DEFAULT 0,
                    avg_confidence DOUBLE DEFAULT 0.0,
                    period_days INT,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_knowledge_base (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    category VARCHAR(100),
                    topic VARCHAR(255),
                    title VARCHAR(255),
                    content TEXT,
                    tags VARCHAR(255),
                    source VARCHAR(255),
                    confidence DOUBLE DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_prompts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    prompt_name VARCHAR(100) UNIQUE,
                    prompt_type VARCHAR(50),
                    prompt_text TEXT,
                    is_default TINYINT(1) DEFAULT 0,
                    is_active TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_strategies (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) UNIQUE,
                    strategy_name VARCHAR(100),
                    display_name VARCHAR(255),
                    description TEXT,
                    holding_period VARCHAR(50),
                    risk_profile VARCHAR(50),
                    indicators_priority TEXT,
                    min_confidence DOUBLE DEFAULT 60.0,
                    config_json TEXT,
                    is_active TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_analysis_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cache_key VARCHAR(255) UNIQUE,
                    strategy VARCHAR(50),
                    risk_level VARCHAR(50),
                    result_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                -- Daily Upload tables (Money Flow Analysis)
                CREATE TABLE IF NOT EXISTS daily_uploads (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    upload_date DATE DEFAULT (CURRENT_DATE),
                    filename VARCHAR(255),
                    total_stocks INT DEFAULT 0,
                    file_path TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS daily_stock_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    upload_id INT,
                    stock_code VARCHAR(50) NOT NULL,
                    date DATE,
                    open_price DOUBLE,
                    high_price DOUBLE,
                    low_price DOUBLE,
                    close_price DOUBLE,
                    volume BIGINT,
                    sma_20 DOUBLE,
                    sma_50 DOUBLE,
                    rsi DOUBLE,
                    macd DOUBLE,
                    macd_signal DOUBLE,
                    foreign_net_buy DOUBLE DEFAULT 0,
                    foreign_accumulation_days INT DEFAULT 0,
                    broker_buy DOUBLE DEFAULT 0,
                    broker_sell DOUBLE DEFAULT 0,
                    ihsg_change DOUBLE DEFAULT 0,
                    sector VARCHAR(100) DEFAULT '',
                    additional_data TEXT,
                    FOREIGN KEY (upload_id) REFERENCES daily_uploads(id)
                );
                CREATE TABLE IF NOT EXISTS day_trade_predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_data_id INT,
                    stock_code VARCHAR(50) NOT NULL,
                    prediction_date DATE,
                    trade_signal VARCHAR(10),
                    confidence DOUBLE,
                    expected_profit_percentage DOUBLE,
                    risk_level VARCHAR(20),
                    reasoning TEXT,
                    features_used TEXT,
                    actual_profit DOUBLE,
                    was_correct TINYINT(1) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_data_id) REFERENCES daily_stock_data(id)
                );
                CREATE TABLE IF NOT EXISTS upload_analysis_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    upload_id INT,
                    analysis_date DATE,
                    total_buy_signals INT DEFAULT 0,
                    total_sell_signals INT DEFAULT 0,
                    total_hold_signals INT DEFAULT 0,
                    confidence_score DOUBLE,
                    results_data TEXT,
                    FOREIGN KEY (upload_id) REFERENCES daily_uploads(id)
                );
                CREATE TABLE IF NOT EXISTS ai_training_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(50),
                    prediction_date DATE,
                    features_used TEXT,
                    actual_outcome VARCHAR(10),
                    ai_prediction VARCHAR(10),
                    ai_confidence DOUBLE,
                    accuracy DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_training_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    training_type VARCHAR(50) NOT NULL,
                    model_name VARCHAR(100),
                    accuracy DOUBLE,
                    `precision` DOUBLE,
                    `recall` DOUBLE,
                    f1_score DOUBLE,
                    parameters TEXT,
                    duration_seconds DOUBLE,
                    status VARCHAR(20) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        else:
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
                    strategy TEXT,
                    score_type TEXT,
                    score_value REAL DEFAULT 0,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy REAL DEFAULT 0.0,
                    winrate REAL DEFAULT 0,
                    avg_profit_pct REAL DEFAULT 0,
                    total_profit_pct REAL DEFAULT 0,
                    avg_confidence REAL DEFAULT 0.0,
                    period_days INTEGER,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    topic TEXT,
                    title TEXT,
                    content TEXT,
                    tags TEXT,
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_name TEXT UNIQUE,
                    prompt_type TEXT,
                    prompt_text TEXT,
                    is_default INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    strategy_name TEXT,
                    display_name TEXT,
                    description TEXT,
                    holding_period TEXT,
                    risk_profile TEXT,
                    indicators_priority TEXT,
                    min_confidence REAL DEFAULT 60.0,
                    config_json TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ai_analysis_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE,
                    strategy TEXT,
                    risk_level TEXT,
                    result_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                -- Daily Upload tables (Money Flow Analysis)
                CREATE TABLE IF NOT EXISTS daily_uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    upload_date DATE DEFAULT (date('now')),
                    filename TEXT,
                    total_stocks INTEGER DEFAULT 0,
                    file_path TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS daily_stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    upload_id INTEGER,
                    stock_code TEXT NOT NULL,
                    date DATE,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume INTEGER,
                    sma_20 REAL,
                    sma_50 REAL,
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    foreign_net_buy REAL DEFAULT 0,
                    foreign_accumulation_days INTEGER DEFAULT 0,
                    broker_buy REAL DEFAULT 0,
                    broker_sell REAL DEFAULT 0,
                    ihsg_change REAL DEFAULT 0,
                    sector TEXT DEFAULT '',
                    additional_data TEXT,
                    FOREIGN KEY (upload_id) REFERENCES daily_uploads(id)
                );
                CREATE TABLE IF NOT EXISTS day_trade_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_data_id INTEGER,
                    stock_code TEXT NOT NULL,
                    prediction_date DATE,
                    trade_signal TEXT,
                    confidence REAL,
                    expected_profit_percentage REAL,
                    risk_level TEXT,
                    reasoning TEXT,
                    features_used TEXT,
                    actual_profit REAL,
                    was_correct INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_data_id) REFERENCES daily_stock_data(id)
                );
                CREATE TABLE IF NOT EXISTS upload_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    upload_id INTEGER,
                    analysis_date DATE,
                    total_buy_signals INTEGER DEFAULT 0,
                    total_sell_signals INTEGER DEFAULT 0,
                    total_hold_signals INTEGER DEFAULT 0,
                    confidence_score REAL,
                    results_data TEXT,
                    FOREIGN KEY (upload_id) REFERENCES daily_uploads(id)
                );
                CREATE TABLE IF NOT EXISTS ai_training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT,
                    prediction_date DATE,
                    features_used TEXT,
                    actual_outcome TEXT,
                    ai_prediction TEXT,
                    ai_confidence REAL,
                    accuracy REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
