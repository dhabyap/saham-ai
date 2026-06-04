from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.ai.learning_engine import LearningEngine
from app.ai.training_engine import TrainingEngine
from app.database import ai_crud
from app.config import Config

router = APIRouter(prefix="/api/learning", tags=["ai-learning"])
_learning_engine = None
_training_engine = None


def get_learning_engine():
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine


def get_training_engine():
    global _training_engine
    if _training_engine is None:
        _training_engine = TrainingEngine()
    return _training_engine


# ─── Prediction History ─────────────────────────────────────────

@router.get("/predictions")
def get_predictions(limit: int = Query(50, ge=1, le=500),
                    unevaluated: bool = False):
    return {"predictions": ai_crud.get_predictions(limit, unevaluated_only=unevaluated)}


@router.get("/predictions/{pred_id}")
def get_prediction(pred_id: int):
    pred = ai_crud.get_prediction_by_id(pred_id)
    if not pred:
        raise HTTPException(404, "Prediction not found")
    return pred


# ─── Evaluation ─────────────────────────────────────────────────

@router.post("/evaluate")
def evaluate_predictions(days: int = Query(7, ge=1, le=90)):
    return get_learning_engine().evaluate_predictions(eval_days=days)


# ─── Performance & Scores ───────────────────────────────────────

@router.get("/performance")
def get_performance():
    return get_learning_engine().get_performance_summary()


@router.get("/scores")
def get_scores():
    return {"scores": ai_crud.get_latest_model_scores()}


@router.get("/accuracy-chart")
def get_accuracy_chart():
    return get_learning_engine().get_accuracy_chart_data()


# ─── User Config ────────────────────────────────────────────────

class UserConfigUpdate(BaseModel):
    user_id: int = 1
    risk_level: Optional[str] = None
    strategy: Optional[str] = None
    confidence_threshold: Optional[float] = None
    auto_learning: Optional[int] = None
    ai_provider: Optional[str] = None


@router.get("/config/{user_id}")
def get_user_config(user_id: int = 1):
    return ai_crud.get_or_create_user_config(user_id)


@router.put("/config")
def update_user_config(req: UserConfigUpdate):
    ai_crud.update_user_config(
        req.user_id,
        risk_level=req.risk_level,
        strategy=req.strategy,
        confidence_threshold=req.confidence_threshold,
        auto_learning=req.auto_learning,
        ai_provider=req.ai_provider,
    )
    return {"status": "ok", "config": ai_crud.get_or_create_user_config(req.user_id)}


# ─── Indicator Weights ──────────────────────────────────────────

class WeightsUpdate(BaseModel):
    user_id: int = 0
    rsi_weight: Optional[float] = None
    macd_weight: Optional[float] = None
    volume_weight: Optional[float] = None
    trend_weight: Optional[float] = None
    sentiment_weight: Optional[float] = None
    support_resistance_weight: Optional[float] = None


@router.get("/weights/{user_id}")
def get_weights(user_id: int = 0):
    return ai_crud.get_or_create_weights(user_id)


@router.put("/weights")
def update_weights(req: WeightsUpdate):
    ai_crud.update_indicator_weights(
        req.user_id,
        rsi_weight=req.rsi_weight,
        macd_weight=req.macd_weight,
        volume_weight=req.volume_weight,
        trend_weight=req.trend_weight,
        sentiment_weight=req.sentiment_weight,
        support_resistance_weight=req.support_resistance_weight,
    )
    return {"status": "ok", "weights": ai_crud.get_or_create_weights(req.user_id)}


@router.post("/weights/adjust")
def auto_adjust_weights():
    return get_learning_engine().adjust_weights_auto()


# ─── Feedback ───────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    user_id: int = 1
    stock_code: str
    prediction_id: Optional[int] = None
    feedback_value: str
    comment: Optional[str] = None


@router.post("/feedback")
def submit_feedback(req: FeedbackCreate):
    user = ai_crud.get_user(req.user_id)
    if not user:
        user = ai_crud.add_user(req.user_id)
    ai_crud.save_feedback(
        user["id"], req.stock_code, req.prediction_id,
        "user", req.feedback_value, req.comment,
    )
    return {"status": "ok", "message": "Feedback saved"}


@router.get("/feedback")
def get_feedback(limit: int = 50):
    return {"feedback": ai_crud.get_feedback(limit)}


@router.get("/feedback/stats")
def feedback_stats():
    return ai_crud.get_feedback_stats()


# ─── Knowledge Base ─────────────────────────────────────────────

@router.get("/knowledge/search")
def search_knowledge(query: str, category: Optional[str] = None):
    from app.ai.knowledge_base import search_knowledge as kb_search
    return {"results": kb_search(query, category)}


@router.get("/knowledge/categories")
def knowledge_categories():
    return {"categories": ai_crud.get_knowledge_categories()}


@router.get("/knowledge/{category}")
def knowledge_by_category(category: str):
    return {"items": ai_crud.get_knowledge_by_category(category)}


# ─── Strategies ─────────────────────────────────────────────────

@router.get("/strategies")
def list_strategies(active_only: bool = False):
    return {"strategies": ai_crud.get_strategies(active_only)}


# ─── Prompts ────────────────────────────────────────────────────

class PromptUpdate(BaseModel):
    prompt_text: str


@router.get("/prompts")
def list_prompts():
    return {"prompts": ai_crud.get_all_prompts()}


@router.get("/prompts/{prompt_name}")
def get_prompt(prompt_name: str):
    prompt = ai_crud.get_prompt(prompt_name)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    return prompt


@router.put("/prompts/{prompt_name}")
def update_prompt(prompt_name: str, req: PromptUpdate):
    ai_crud.update_prompt(prompt_name, req.prompt_text)
    return {"status": "ok"}


# ─── Training ───────────────────────────────────────────────────

class TrainingRequest(BaseModel):
    model_type: str = "random_forest"
    stocks: Optional[list] = None
    period: str = "6mo"


@router.post("/train")
def train_model(req: TrainingRequest):
    training_engine = get_training_engine()
    X, y, labels = training_engine.prepare_training_data(
        period=req.period, stocks=req.stocks
    )
    if len(X) < 50:
        raise HTTPException(400, f"Not enough data ({len(X)} samples, need 50+)")

    if req.model_type == "random_forest":
        result = training_engine.train_random_forest(X, y)
    elif req.model_type == "xgboost":
        result = training_engine.train_xgboost(X, y)
    elif req.model_type == "lightgbm":
        result = training_engine.train_lightgbm(X, y)
    else:
        raise HTTPException(400, f"Unknown model type: {req.model_type}")

    result["samples"] = len(X)
    result["stocks"] = labels
    return result


@router.get("/training/logs")
def training_logs(limit: int = 20):
    return {"logs": ai_crud.get_training_logs(limit)}


@router.get("/training/status")
def training_status():
    return get_training_engine().get_training_status()


# ─── Backtesting ────────────────────────────────────────────────

@router.get("/backtest/{code}")
def backtest(code: str, strategy: str = "swing", period: str = "6mo"):
    return get_training_engine().backtest_strategy(code, strategy, period)


# ─── Knowledge Seed ─────────────────────────────────────────────

@router.post("/knowledge/seed")
def seed_knowledge():
    from app.ai.knowledge_base import seed_knowledge_base
    seed_knowledge_base()
    return {"status": "ok", "message": "Knowledge base seeded"}


# ─── Provider Info ──────────────────────────────────────────────

@router.get("/providers")
def list_providers():
    from app.ai.providers import get_available_providers
    return {"providers": get_available_providers()}
