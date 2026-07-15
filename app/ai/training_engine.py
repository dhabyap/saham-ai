import time
import numpy as np
from datetime import datetime, timedelta

from app.services.stock_service import STOCK_LIST, fetch_stock_data, calculate_indicators
from app.database import ai_crud


class TrainingEngine:
    def __init__(self):
        self.models = {}

    def prepare_training_data(self, period="6mo", stocks=None):
        if stocks is None:
            stocks = list(STOCK_LIST.keys())[:10]

        X = []
        y = []
        features_list = []
        labels = []

        for code in stocks:
            try:
                data = fetch_stock_data(code, period=period)
                if not data:
                    continue

                df = calculate_indicators(data["history"])
                if df is None or len(df) < 50:
                    continue

                for i in range(30, len(df) - 5):
                    row = df.iloc[i]
                    future_close = df["Close"].iloc[i + 5]
                    current_close = row["Close"]
                    change_pct = ((future_close - current_close) / current_close) * 100

                    features = [
                        float(row["RSI"]) if not np.isnan(row["RSI"]) else 50,
                        float(row["MACD"]) if not np.isnan(row["MACD"]) else 0,
                        float(row["MACD_Signal"]) if not np.isnan(row["MACD_Signal"]) else 0,
                        float(row["MACD_Hist"]) if not np.isnan(row["MACD_Hist"]) else 0,
                        float(row["MA20"]) if not np.isnan(row["MA20"]) else current_close,
                        float(row["MA50"]) if not np.isnan(row["MA50"]) else current_close,
                        float(row["Volume"]) if not np.isnan(row["Volume"]) else 0,
                        float(row["Volume_MA"]) if not np.isnan(row["Volume_MA"]) else 0,
                        float(row["Close"]),
                        float(row["High"] - row["Low"]),
                        float(row["Close"] - row["Open"]),
                    ]
                    X.append(features)
                    if change_pct > 2:
                        y.append(1)
                    elif change_pct < -2:
                        y.append(-1)
                    else:
                        y.append(0)

                features_list.append(code)
                labels.append(f"{code}: {len(df)} days")

            except Exception as e:
                print(f"  Error preparing {code}: {e}")

        return np.array(X), np.array(y), features_list

    def train_random_forest(self, X, y):
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

            if len(X) < 50:
                return {"error": "Not enough data"}

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            model = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
            )
            start = time.time()
            model.fit(X_train, y_train)
            duration = time.time() - start

            y_pred = model.predict(X_test)
            accuracy = float(accuracy_score(y_test, y_pred))
            precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
            recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
            f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

            self.models["random_forest"] = model

            ai_crud.save_training_log(
                training_type="random_forest",
                model_name="RandomForest",
                accuracy=round(accuracy, 4),
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1_score=round(f1, 4),
                parameters={"n_estimators": 100, "max_depth": 10},
                duration_seconds=round(duration, 2),
                status="completed",
            )

            importances = model.feature_importances_
            feature_names = [
                "RSI", "MACD", "MACD_Signal", "MACD_Hist",
                "MA20", "MA50", "Volume", "Volume_MA",
                "Close", "High-Low", "Close-Open",
            ]
            top_features = sorted(
                zip(feature_names, importances),
                key=lambda x: x[1], reverse=True
            )[:5]

            return {
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "samples": len(X),
                "top_features": top_features,
                "duration": round(duration, 2),
            }

        except ImportError:
            return {"error": "scikit-learn not installed"}
        except Exception as e:
            ai_crud.save_training_log(
                training_type="random_forest",
                status=f"failed: {e}",
            )
            return {"error": str(e)}

    def train_xgboost(self, X, y):
        try:
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

            if len(X) < 50:
                return {"error": "Not enough data"}

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            model = xgb.XGBClassifier(
                n_estimators=100, max_depth=6,
                learning_rate=0.1, random_state=42,
                use_label_encoder=False, eval_metric="mlogloss",
            )
            start = time.time()
            model.fit(X_train, y_train)
            duration = time.time() - start

            y_pred = model.predict(X_test)
            accuracy = float(accuracy_score(y_test, y_pred))
            precision = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
            recall = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
            f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

            self.models["xgboost"] = model

            ai_crud.save_training_log(
                training_type="xgboost",
                model_name="XGBoost",
                accuracy=round(accuracy, 4),
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1_score=round(f1, 4),
                parameters={"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1},
                duration_seconds=round(duration, 2),
                status="completed",
            )

            return {
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "samples": len(X),
                "duration": round(duration, 2),
            }

        except ImportError:
            return {"error": "xgboost not installed"}
        except Exception as e:
            ai_crud.save_training_log(
                training_type="xgboost",
                status=f"failed: {e}",
            )
            return {"error": str(e)}

    def train_lightgbm(self, X, y):
        try:
            import lightgbm as lgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score

            if len(X) < 50:
                return {"error": "Not enough data"}

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            model = lgb.LGBMClassifier(
                n_estimators=100, max_depth=6, learning_rate=0.1,
                random_state=42, verbose=-1,
            )
            start = time.time()
            model.fit(X_train, y_train)
            duration = time.time() - start

            y_pred = model.predict(X_test)
            accuracy = float(accuracy_score(y_test, y_pred))

            self.models["lightgbm"] = model

            ai_crud.save_training_log(
                training_type="lightgbm",
                model_name="LightGBM",
                accuracy=round(accuracy, 4),
                parameters={"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1},
                duration_seconds=round(duration, 2),
                status="completed",
            )

            return {
                "accuracy": round(accuracy, 4),
                "samples": len(X),
                "duration": round(duration, 2),
            }

        except ImportError:
            return {"error": "lightgbm not installed"}
        except Exception as e:
            ai_crud.save_training_log(
                training_type="lightgbm",
                status=f"failed: {e}",
            )
            return {"error": str(e)}

    def backtest_strategy(self, code, strategy="swing", period="6mo"):
        try:
            data = fetch_stock_data(code, period=period)
            if not data:
                return {"error": f"No data for {code}"}

            df = calculate_indicators(data["history"])
            if df is None or len(df) < 30:
                return {"error": "Not enough data"}

            signals = []
            for i in range(30, len(df)):
                row = df.iloc[i]
                rsi = row["RSI"]
                macd = row["MACD"]
                macd_signal = row["MACD_Signal"]
                prev_macd = df["MACD"].iloc[i - 1]
                prev_macd_signal = df["MACD_Signal"].iloc[i - 1]

                score = 0
                if not np.isnan(rsi):
                    if rsi < 30:
                        score += 2
                    elif rsi > 70:
                        score -= 2

                if "Bullish" in str(data.get("trend", "")):
                    score += 1

                if not np.isnan(macd) and not np.isnan(macd_signal):
                    if macd > macd_signal and prev_macd <= prev_macd_signal:
                        score += 2
                    elif macd < macd_signal and prev_macd >= prev_macd_signal:
                        score -= 2

                if strategy == "scalping":
                    threshold = 1
                elif strategy == "swing":
                    threshold = 2
                else:
                    threshold = 3

                if score >= threshold:
                    signal = "BUY"
                elif score <= -threshold:
                    signal = "SELL"
                else:
                    signal = "HOLD"

                signals.append({
                    "date": df.index[i].isoformat()[:10],
                    "close": float(row["Close"]),
                    "signal": signal,
                    "score": score,
                })

            trades = []
            in_position = False
            entry_price = 0
            entry_date = ""
            for s in signals:
                if s["signal"] == "BUY" and not in_position:
                    in_position = True
                    entry_price = s["close"]
                    entry_date = s["date"]
                elif s["signal"] == "SELL" and in_position:
                    profit_pct = ((s["close"] - entry_price) / entry_price) * 100
                    trades.append({
                        "entry_date": entry_date,
                        "exit_date": s["date"],
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(s["close"], 2),
                        "profit_pct": round(profit_pct, 2),
                        "return_pct": round(profit_pct, 2),
                        "result": "win" if profit_pct > 0 else "loss",
                    })
                    in_position = False

            if trades:
                wins = sum(1 for t in trades if t["profit_pct"] > 0)
                losses = sum(1 for t in trades if t["profit_pct"] <= 0)
                total_return = sum(t["profit_pct"] for t in trades)
                avg_return = total_return / len(trades)
                winrate = (wins / len(trades) * 100) if trades else 0
            else:
                wins = losses = total_return = avg_return = winrate = 0

            return {
                "stock_code": code,
                "strategy": strategy,
                "period": period,
                "total_signals": len(signals),
                "total_trades": len(trades),
                "wins": wins,
                "losses": losses,
                "winrate": round(winrate, 2),
                "total_return_pct": round(total_return, 2),
                "avg_return_pct": round(avg_return, 2),
                "trades": trades[:20],
            }

        except Exception as e:
            return {"error": str(e)}

    def get_training_status(self):
        logs = ai_crud.get_training_logs(limit=10)
        return {
            "models_loaded": list(self.models.keys()),
            "recent_training": logs,
        }
