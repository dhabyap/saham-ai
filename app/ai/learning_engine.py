from datetime import datetime, timedelta
from app.database import ai_crud
from app.config import Config
from app.database.foreign_flow_models import get_accumulation_status, get_foreign_flow


class LearningEngine:
    def __init__(self):
        self.weights = ai_crud.get_or_create_weights(user_id=0)

    def evaluate_predictions(self, eval_days=7):
        predictions = ai_crud.get_predictions_for_evaluation(eval_days)
        if not predictions:
            return {"evaluated": 0, "message": "No predictions to evaluate"}

        from app.services.stock_service import get_latest_data
        evaluated = 0

        for pred in predictions:
            try:
                data = get_latest_data(pred["stock_code"])
                if not data:
                    continue

                current_price = data["price"]
                pred_price = pred["price_at_prediction"]
                days_since = (datetime.now() - datetime.fromisoformat(
                    pred["created_at"])).days

                if pred["prediction"] == "BUY":
                    profit_pct = ((current_price - pred_price) / pred_price) * 100
                    actual = "SUCCESS" if profit_pct > 0 else "FAIL"
                elif pred["prediction"] == "SELL":
                    profit_pct = ((pred_price - current_price) / pred_price) * 100
                    actual = "SUCCESS" if profit_pct > 0 else "FAIL"
                else:
                    change_pct = abs((current_price - pred_price) / pred_price) * 100
                    profit_pct = 0
                    actual = "SUCCESS" if change_pct < 2 else "FAIL"

                ai_crud.update_prediction_result(
                    pred["id"], actual, current_price,
                    profit_pct=round(profit_pct, 2),
                )
                evaluated += 1

            except Exception as e:
                print(f"  Evaluation error {pred.get('stock_code')}: {e}")

        if evaluated:
            self._update_model_scores()

        return {"evaluated": evaluated, "message": f"{evaluated} predictions evaluated"}

    def _update_model_scores(self):
        predictions = ai_crud.get_predictions(limit=1000)
        if not predictions:
            return

        total = len(predictions)
        correct = sum(1 for p in predictions if p.get("actual_result") == "SUCCESS")
        winrate = (correct / total * 100) if total > 0 else 0
        profits = [p.get("profit_pct", 0) or 0 for p in predictions if p.get("profit_pct")]
        avg_profit = sum(profits) / len(profits) if profits else 0
        total_profit = sum(profits)

        ai_crud.save_model_score(
            "accuracy_overall", round(winrate, 2),
            total, correct, round(winrate, 2),
            round(avg_profit, 2), round(total_profit, 2),
        )

        now = datetime.now()
        for days, score_type in [(7, "accuracy_7d"), (30, "accuracy_30d")]:
            cutoff = (now - timedelta(days=days)).isoformat()
            recent = [p for p in predictions
                      if p.get("created_at", "") >= cutoff]
            if recent:
                r_total = len(recent)
                r_correct = sum(
                    1 for p in recent if p.get("actual_result") == "SUCCESS"
                )
                r_winrate = (r_correct / r_total * 100) if r_total > 0 else 0
                r_profits = [p.get("profit_pct", 0) or 0 for p in recent
                             if p.get("profit_pct")]
                r_avg = sum(r_profits) / len(r_profits) if r_profits else 0
                r_total_profit = sum(r_profits)

                ai_crud.save_model_score(
                    score_type, round(r_winrate, 2),
                    r_total, r_correct, round(r_winrate, 2),
                    round(r_avg, 2), round(r_total_profit, 2),
                    period_days=days,
                )

        ai_crud.save_model_score(
            "winrate", round(winrate, 2),
            total, correct, round(winrate, 2),
            period_days=0,
        )

        if profits:
            ai_crud.save_model_score(
                "avg_profit", round(avg_profit, 2),
                period_days=0,
            )

    def adjust_weights_auto(self):
        predictions = ai_crud.get_predictions(limit=500)
        if len(predictions) < 20:
            return {"adjusted": False, "message": "Not enough data (need 20+)"}

        from app.services.analysis_service import AnalysisService
        service = AnalysisService()

        correct_buys = 0
        total_buys = 0
        for p in predictions:
            if p.get("prediction") == "BUY":
                total_buys += 1
                if p.get("actual_result") == "SUCCESS":
                    correct_buys += 1

        buy_winrate = (correct_buys / total_buys * 100) if total_buys > 0 else 0

        weights = ai_crud.get_or_create_weights(user_id=0)

        adjustments = {}
        if buy_winrate < 40 and total_buys >= 10:
            current = weights.get("trend_weight", 1.0)
            new_val = min(2.0, current * 1.1)
            ai_crud.update_indicator_weights(trend_weight=new_val)
            adjustments["trend_weight"] = f"{current:.2f} -> {new_val:.2f} (increased)"

        if buy_winrate > 70 and total_buys >= 10:
            current = weights.get("volume_weight", 1.0)
            new_val = min(2.0, current * 1.05)
            ai_crud.update_indicator_weights(volume_weight=new_val)
            adjustments["volume_weight"] = f"{current:.2f} -> {new_val:.2f} (increased)"

        self.weights = ai_crud.get_or_create_weights(user_id=0)

        return {
            "adjusted": bool(adjustments),
            "adjustments": adjustments,
            "buy_winrate": round(buy_winrate, 2),
            "total_buys": total_buys,
        }

    def get_scored_recommendation(self, data, strategy="swing",
                                   risk_level="moderate"):
        weights = ai_crud.get_or_create_weights(user_id=0)
        config = {"risk_level": risk_level, "strategy": strategy}

        score = 0
        reasons = []
        details = {}

        # === FOREIGN FLOW — PRIMARY GATE ===
        stock_code = data.get("stock_code", "").replace(".JK", "")
        foreign_score = 0
        foreign_reason = ""
        try:
            accum = get_accumulation_status(stock_code)
            if accum:
                data["accumulation_days"] = accum.get("accumulation_days", 0)
                data["accumulation_status"] = accum.get("status", "neutral")
                accum_days = accum.get("accumulation_days", 0)
                status = accum.get("status", "neutral")
                if accum_days >= 5 and status == "accumulating":
                    foreign_score = 5
                    foreign_reason = f"Asing akumulasi {accum_days} hari berturut-turut"
                elif accum_days >= 3:
                    foreign_score = 4
                    foreign_reason = f"Asing mulai akumulasi {accum_days} hari"
                elif accum_days >= 1:
                    foreign_score = 2
                    foreign_reason = f"Asing beli 1 hari ({accum_days}d)"
                elif status == "distributing":
                    foreign_score = -3
                    foreign_reason = f"Asing distribusi, waspada"
                else:
                    foreign_score = 0
                    foreign_reason = "Netral"

            flow = get_foreign_flow(stock_code, days=5)
            if flow:
                net = sum(r.get("foreign_net", 0) for r in flow)
                data["foreign_net_buy"] = round(net, 0)
                if net > 0:
                    foreign_score += 2
                    foreign_reason += f" | Net asing 5hari: +Rp{net:,.0f}"
                elif net < 0:
                    foreign_score -= 2
                    foreign_reason += f" | Net asing 5hari: Rp{net:,.0f} (jual)"
                else:
                    foreign_reason += " | Net asing 5hari: flat"
            else:
                foreign_reason = "Data asing tidak tersedia"
        except Exception:
            foreign_reason = "Gagal ambil data asing"

        data["foreign_score"] = foreign_score
        data["foreign_reason"] = foreign_reason
        if foreign_score > 0:
            score += foreign_score
            reasons.append(foreign_reason)
        elif foreign_score < 0:
            score += foreign_score
            reasons.append(foreign_reason)
        details["foreign_flow"] = {"score": foreign_score, "reason": foreign_reason}

        # Teknikal sebagai supplementary insight
        rsi = data.get("rsi")
        if rsi is not None:
            rsi_weight = weights.get("rsi_weight", 1.0)
            if rsi < 30:
                s = 2 * rsi_weight
                score += s
                reasons.append(f"RSI oversold ({rsi:.1f}) +{s:.1f}")
            elif rsi > 70:
                s = -2 * rsi_weight
                score += s
                reasons.append(f"RSI overbought ({rsi:.1f}) {s:.1f}")
            else:
                s = 0.5 * rsi_weight
                score += s
                reasons.append(f"RSI normal ({rsi:.1f}) +{s:.1f}")
            details["rsi"] = {"value": rsi, "weight": rsi_weight, "contribution": s}

        trend = data.get("trend", "")
        trend_weight = weights.get("trend_weight", 1.0)
        if "Bullish" in trend:
            s = 2 * trend_weight
            score += s
            reasons.append(f"Trend bullish +{s:.1f}")
        elif "Bearish" in trend:
            s = -2 * trend_weight
            score += s
            reasons.append(f"Trend bearish {s:.1f}")
        else:
            s = 0 * trend_weight
            score += s
            reasons.append(f"Trend sideways +{s:.1f}")
        details["trend"] = {"value": trend, "weight": trend_weight, "contribution": s}

        macd = data.get("macd_status", "")
        macd_weight = weights.get("macd_weight", 1.0)
        if macd == "Golden Cross":
            s = 2 * macd_weight
            score += s
            reasons.append(f"MACD golden cross +{s:.1f}")
        elif macd == "Death Cross":
            s = -2 * macd_weight
            score += s
            reasons.append(f"MACD death cross {s:.1f}")
        elif "Bullish" in macd:
            s = 1 * macd_weight
            score += s
            reasons.append(f"MACD bullish +{s:.1f}")
        elif "Bearish" in macd:
            s = -1 * macd_weight
            score += s
            reasons.append(f"MACD bearish {s:.1f}")
        details["macd"] = {"value": macd, "weight": macd_weight, "contribution": s}

        volume_weight = weights.get("volume_weight", 1.0)
        if data.get("volume_spike"):
            s = 1.5 * volume_weight
            score += s
            reasons.append(f"Volume spike +{s:.1f}")
            details["volume"] = {"spike": True, "weight": volume_weight, "contribution": s}

        sr_weight = weights.get("support_resistance_weight", 1.0)
        if data.get("near_support"):
            s = 1.5 * sr_weight
            score += s
            reasons.append(f"Near support +{s:.1f}")
        if data.get("near_resistance"):
            s = -1.5 * sr_weight
            score += s
            reasons.append(f"Near resistance {s:.1f}")
        details["support_resistance"] = {
            "near_support": data.get("near_support"),
            "near_resistance": data.get("near_resistance"),
            "weight": sr_weight,
        }

        if config["risk_level"] == "conservative":
            if abs(score) < 2:
                return "HOLD", max(50, min(99, 50 + score * 5)), "; ".join(reasons), details
            threshold = 3
        elif config["risk_level"] == "aggressive":
            threshold = 1.5
        else:
            threshold = 2

        # FOREIGN FLOW GATE: tanpa akumulasi asing, max HOLD
        if score >= threshold:
            if foreign_score > 0:
                recommendation = "BUY"
            else:
                recommendation = "HOLD"
                reasons.append("Asing tidak akumulasi")
        elif score <= -threshold:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        confidence = min(99, max(1, 50 + score * 8))
        confidence = max(confidence, Config.MIN_CONFIDENCE_THRESHOLD)

        return recommendation, int(confidence), "; ".join(reasons), details

    def get_performance_summary(self):
        scores = ai_crud.get_latest_model_scores()
        feedback = ai_crud.get_feedback_stats()
        predictions = ai_crud.get_predictions(limit=5)
        recent = [
            {"stock": p["stock_code"], "prediction": p["prediction"],
             "actual": p.get("actual_result", "Pending"),
             "confidence": p.get("confidence"),
             "profit": p.get("profit_pct"),
             "date": str(p.get("created_at", ""))[:10]}
            for p in predictions
        ]

        return {
            "scores": scores,
            "feedback": feedback,
            "recent_predictions": recent,
        }

    def get_accuracy_chart_data(self):
        all_scores = ai_crud.get_all_model_scores()
        chart_data = {"accuracy_7d": [], "accuracy_30d": [], "accuracy_overall": [],
                      "winrate": [], "dates": []}
        for s in all_scores:
            if s["score_type"] in chart_data:
                chart_data[s["score_type"]].append(s["score_value"])
        return chart_data
