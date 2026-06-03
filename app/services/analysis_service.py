from app.services.stock_service import get_latest_data
from app.ai.ai_analyzer import AIAnalyzer
from app.ai.learning_engine import LearningEngine
from app.database import ai_crud
from app.config import Config


class AnalysisService:
    def __init__(self):
        self.ai = AIAnalyzer()
        self.learning = LearningEngine()

    def analyze_stock(self, code, use_ai=True, strategy=None, risk_level=None,
                       user_id=None):
        data = get_latest_data(code)
        if data is None:
            return {"error": f"Tidak dapat mengambil data untuk {code}"}

        df = data.pop("dataframe", None)

        if user_id:
            user_config = ai_crud.get_or_create_user_config(user_id)
            strategy = strategy or user_config.get("strategy", Config.DEFAULT_STRATEGY)
            risk_level = risk_level or user_config.get("risk_level", Config.DEFAULT_RISK_LEVEL)
        else:
            strategy = strategy or Config.DEFAULT_STRATEGY
            risk_level = risk_level or Config.DEFAULT_RISK_LEVEL

        if use_ai and self.ai.is_available():
            ai_result = self.ai.analyze(data, strategy=strategy, risk_level=risk_level)
            if ai_result:
                recommendation = ai_result.get("recommendation", "HOLD")
                confidence = ai_result.get("confidence", 50)
                reason = ai_result.get("reasoning", "")
                full_analysis = ai_result.get("full_analysis", "")
                trend = ai_result.get("trend", data["trend"])
            else:
                recommendation, confidence, reason, details = self.learning.get_scored_recommendation(
                    data, strategy, risk_level,
                )
                full_analysis = reason
                trend = data["trend"]
        else:
            recommendation, confidence, reason, details = self.learning.get_scored_recommendation(
                data, strategy, risk_level,
            )
            full_analysis = reason
            trend = data["trend"]

        result = {
            **data,
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "full_analysis": full_analysis,
            "trend": trend,
            "strategy": strategy,
            "risk_level": risk_level,
        }

        pred_id = ai_crud.save_prediction(
            stock_code=code.upper(),
            stock_name=data["stock_name"],
            prediction=recommendation,
            confidence=confidence,
            price_at_prediction=data["price"],
            strategy=strategy,
            ai_provider=self.ai.provider.name if self.ai.provider else "rule-based",
        )

        if df is not None:
            data["dataframe"] = df

        return result

    def _rule_based_recommendation(self, data):
        recommendation, confidence, reason, _ = self.learning.get_scored_recommendation(
            data, Config.DEFAULT_STRATEGY, Config.DEFAULT_RISK_LEVEL,
        )
        return recommendation, confidence, reason

    def _calculate_confidence(self, data):
        _, confidence, _, _ = self.learning.get_scored_recommendation(
            data, Config.DEFAULT_STRATEGY, Config.DEFAULT_RISK_LEVEL,
        )
        return min(99, max(1, confidence))

    def _generate_reason(self, data):
        _, _, reason, _ = self.learning.get_scored_recommendation(
            data, Config.DEFAULT_STRATEGY, Config.DEFAULT_RISK_LEVEL,
        )
        return reason
