import json
from datetime import datetime, timedelta
from app.database.database import get_db, DB_TYPE


# ─── PREDICTIONS ────────────────────────────────────────────────

def save_prediction(stock_code, stock_name, prediction, confidence,
                    price_at_prediction, price_target=None, strategy='swing',
                    indicators_used=None, ai_provider=None, days_to_eval=7):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ai_predictions
               (stock_code, stock_name, prediction, confidence,
                price_at_prediction, price_target, strategy,
                indicators_used, ai_provider, days_to_eval)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (stock_code.upper(), stock_name, prediction, confidence,
             price_at_prediction, price_target, strategy,
             json.dumps(indicators_used) if indicators_used else None,
             ai_provider, days_to_eval),
        )
        cur = conn.execute("SELECT last_insert_rowid()")
        return cur.fetchone()[0]


def get_predictions(limit=50, unevaluated_only=False):
    with get_db() as conn:
        query = "SELECT * FROM ai_predictions"
        params = []
        if unevaluated_only:
            query += " WHERE evaluated = 0"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_prediction_by_id(pred_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_predictions WHERE id = ?", (pred_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_prediction_result(pred_id, actual_result, price_after,
                              accuracy=None, profit_pct=None):
    with get_db() as conn:
        conn.execute(
            """UPDATE ai_predictions
               SET actual_result = ?, price_after = ?, accuracy = ?,
                   profit_pct = ?, evaluated = 1,
                   evaluated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (actual_result, price_after, accuracy, profit_pct, pred_id),
        )


def get_predictions_for_evaluation(eval_days=7):
    with get_db() as conn:
        cutoff = (datetime.now() - timedelta(days=eval_days)).isoformat()
        cur = conn.execute(
            """SELECT * FROM ai_predictions
               WHERE evaluated = 0 AND created_at < ?
               ORDER BY created_at ASC LIMIT 50""",
            (cutoff,),
        )
        return [dict(row) for row in cur.fetchall()]


# ─── FEEDBACK ───────────────────────────────────────────────────

def save_feedback(user_id, stock_code, prediction_id, feedback_type,
                   feedback_value, comment=None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ai_feedback
               (user_id, stock_code, prediction_id, feedback_type,
                feedback_value, comment)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, stock_code.upper(), prediction_id,
             feedback_type, feedback_value, comment),
        )


def get_feedback(limit=50):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_feedback ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_feedback_stats():
    with get_db() as conn:
        helpful = conn.execute(
            "SELECT COUNT(*) as c FROM ai_feedback WHERE feedback_value = 'helpful'"
        ).fetchone()["c"]
        wrong = conn.execute(
            "SELECT COUNT(*) as c FROM ai_feedback WHERE feedback_value = 'wrong'"
        ).fetchone()["c"]
        bullish = conn.execute(
            "SELECT COUNT(*) as c FROM ai_feedback WHERE feedback_value = 'bullish'"
        ).fetchone()["c"]
        bearish = conn.execute(
            "SELECT COUNT(*) as c FROM ai_feedback WHERE feedback_value = 'bearish'"
        ).fetchone()["c"]
        return {"helpful": helpful, "wrong": wrong,
                "bullish": bullish, "bearish": bearish}


# ─── USER CONFIGS ───────────────────────────────────────────────

def get_or_create_user_config(user_id):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (user_id, f"user_{user_id}"),
        )
        cur = conn.execute(
            "SELECT * FROM ai_user_configs WHERE user_id = ?", (user_id,)
        )
        row = cur.fetchone()
        if row:
            return dict(row)
        cur = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
        db_user = cur.fetchone()
        uid = db_user["id"] if db_user else user_id
        conn.execute(
            "INSERT INTO ai_user_configs (user_id) VALUES (?)", (uid,)
        )
        cur = conn.execute(
            "SELECT * FROM ai_user_configs WHERE user_id = ?", (uid,)
        )
        return dict(cur.fetchone())


def update_user_config(user_id, **kwargs):
    allowed = {"risk_level", "strategy", "confidence_threshold",
               "auto_learning", "ai_provider"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    with get_db() as conn:
        conn.execute(
            f"UPDATE ai_user_configs SET {set_clause} WHERE user_id = ?",
            values,
        )


# ─── INDICATOR WEIGHTS ──────────────────────────────────────────

def get_or_create_weights(user_id=0):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_indicator_weights WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)
        conn.execute(
            "INSERT INTO ai_indicator_weights (user_id) VALUES (?)",
            (user_id,),
        )
        cur = conn.execute(
            "SELECT * FROM ai_indicator_weights WHERE user_id = ?",
            (user_id,),
        )
        return dict(cur.fetchone())


def update_indicator_weights(user_id=0, **kwargs):
    allowed = {"rsi_weight", "macd_weight", "volume_weight",
               "trend_weight", "sentiment_weight",
               "support_resistance_weight"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    with get_db() as conn:
        conn.execute(
            f"UPDATE ai_indicator_weights SET {set_clause} WHERE user_id = ?",
            values,
        )


# ─── MODEL SCORES ───────────────────────────────────────────────

def save_model_score(score_type, score_value, total_predictions=0,
                     correct_predictions=0, winrate=0, avg_profit_pct=0,
                     total_profit_pct=0, period_days=None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ai_model_scores
               (score_type, score_value, total_predictions,
                correct_predictions, winrate, avg_profit_pct,
                total_profit_pct, period_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (score_type, score_value, total_predictions,
             correct_predictions, winrate, avg_profit_pct,
             total_profit_pct, period_days),
        )


def get_latest_model_scores():
    scores = {}
    with get_db() as conn:
        for score_type in ("accuracy_7d", "accuracy_30d", "accuracy_overall",
                           "winrate", "avg_profit"):
            cur = conn.execute(
                """SELECT * FROM ai_model_scores
                   WHERE score_type = ? ORDER BY calculated_at DESC LIMIT 1""",
                (score_type,),
            )
            row = cur.fetchone()
            if row:
                scores[score_type] = dict(row)
        return scores


def get_all_model_scores(limit=100):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_model_scores ORDER BY calculated_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


# ─── KNOWLEDGE BASE ─────────────────────────────────────────────

def add_knowledge(category, title, content, tags=None, source=None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ai_knowledge_base
               (category, title, content, tags, source)
               VALUES (?, ?, ?, ?, ?)""",
            (category, title, content,
             json.dumps(tags) if tags else None, source),
        )


def search_knowledge(query, category=None, limit=20):
    with get_db() as conn:
        sql = """SELECT * FROM ai_knowledge_base
                 WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?)"""
        params = [f"%{query}%", f"%{query}%", f"%{query}%"]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def get_knowledge_categories():
    with get_db() as conn:
        cur = conn.execute(
            "SELECT DISTINCT category FROM ai_knowledge_base ORDER BY category"
        )
        return [row["category"] for row in cur.fetchall()]


def get_knowledge_by_category(category, limit=50):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_knowledge_base WHERE category = ? ORDER BY title LIMIT ?",
            (category, limit),
        )
        return [dict(row) for row in cur.fetchall()]


# ─── STRATEGIES ─────────────────────────────────────────────────

def save_strategy(strategy_name, display_name=None, description=None,
                   holding_period=None, risk_profile=None,
                   indicators_priority=None, min_confidence=60.0):
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO ai_strategies
               (strategy_name, display_name, description, holding_period,
                risk_profile, indicators_priority, min_confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (strategy_name, display_name, description, holding_period,
             risk_profile,
             json.dumps(indicators_priority) if indicators_priority else None,
             min_confidence),
        )


def get_strategies(active_only=False):
    with get_db() as conn:
        query = "SELECT * FROM ai_strategies"
        params = []
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY strategy_name"
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_strategy(name):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_strategies WHERE strategy_name = ?", (name,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


# ─── ANALYSIS CACHE ─────────────────────────────────────────────

def get_analysis_cache(cache_key, today):
    """Return cached result dict if exists and created today, else None."""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT result_json, created_at FROM ai_analysis_cache WHERE cache_key = ?",
            (cache_key,),
        )
        row = cur.fetchone()
        if row:
            created = row["created_at"]
            if created:
                created_date = str(created)[:10]
                if created_date == today:
                    try:
                        return json.loads(row["result_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
        return None

def save_analysis_cache(cache_key, strategy, risk_level, result_dict):
    """Save/update analysis result in cache table."""
    with get_db() as conn:
        result_json = json.dumps(result_dict, default=str)
        if DB_TYPE == "mysql":
            conn.execute(
                """INSERT INTO ai_analysis_cache (cache_key, strategy, risk_level, result_json)
                   VALUES (?, ?, ?, ?)
                   ON DUPLICATE KEY UPDATE result_json = VALUES(result_json), created_at = CURRENT_TIMESTAMP""",
                (cache_key, strategy, risk_level, result_json),
            )
        else:
            conn.execute(
                """INSERT OR REPLACE INTO ai_analysis_cache (cache_key, strategy, risk_level, result_json)
                   VALUES (?, ?, ?, ?)""",
                (cache_key, strategy, risk_level, result_json),
            )

# ─── PROMPTS ────────────────────────────────────────────────────

def save_prompt(prompt_name, prompt_type, prompt_text, is_default=0):
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO ai_prompts
               (prompt_name, prompt_type, prompt_text, is_default)
               VALUES (?, ?, ?, ?)""",
            (prompt_name, prompt_type, prompt_text, is_default),
        )


def get_prompt(prompt_name):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_prompts WHERE prompt_name = ? AND is_active = 1",
            (prompt_name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_prompts_by_type(prompt_type):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_prompts WHERE prompt_type = ? AND is_active = 1 ORDER BY prompt_name",
            (prompt_type,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_all_prompts():
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_prompts ORDER BY prompt_type, prompt_name"
        )
        return [dict(row) for row in cur.fetchall()]


def update_prompt(prompt_name, prompt_text):
    with get_db() as conn:
        conn.execute(
            "UPDATE ai_prompts SET prompt_text = ?, updated_at = CURRENT_TIMESTAMP WHERE prompt_name = ?",
            (prompt_text, prompt_name),
        )


# ─── TRAINING LOGS ──────────────────────────────────────────────

def save_training_log(training_type, model_name=None, accuracy=None,
                       precision=None, recall=None, f1_score=None,
                       parameters=None, duration_seconds=None,
                       status="completed"):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ai_training_logs
               (training_type, model_name, accuracy, precision,
                recall, f1_score, parameters, duration_seconds, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (training_type, model_name, accuracy, precision,
             recall, f1_score,
             json.dumps(parameters) if parameters else None,
             duration_seconds, status),
        )


def get_training_logs(limit=20):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM ai_training_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
