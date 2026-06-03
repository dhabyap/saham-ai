import asyncio
import time
from datetime import datetime

from telegram.ext import Application

from app.services.stock_service import get_latest_data
from app.services.market_service import get_market_summary, get_market_sentiment
from app.database import crud
from app.ai.learning_engine import LearningEngine
from app.config import Config


def update_market_summary():
    try:
        summary = get_market_summary()
        sentiment = get_market_sentiment()
        crud.save_market_summary("market_summary", summary)
        crud.save_market_summary("market_sentiment", sentiment)
        print(f"  ✓ Market summary updated: {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"  ✗ Market summary error: {e}")


def check_watchlist_alerts():
    codes = crud.get_all_watchlist_codes()
    if not codes:
        return

    print(f"  ✓ Checking {len(codes)} watchlist items...")
    alerts = []

    for code in codes:
        time.sleep(1.5)
        try:
            data = get_latest_data(code)
            if not data:
                continue

            rsi = data.get("rsi")
            rsi_status = data.get("rsi_status", "")
            macd = data.get("macd_status", "")
            volume_spike = data.get("volume_spike", False)
            near_resistance = data.get("near_resistance", False)
            near_support = data.get("near_support", False)

            if rsi_status == "Overbought":
                alerts.append(
                    (code, "RSI_OVERBOUGHT", f"⚠️ {code} RSI Overbought: {rsi:.1f}")
                )
            elif rsi_status == "Oversold":
                alerts.append(
                    (code, "RSI_OVERSOLD", f"⚡️ {code} RSI Oversold: {rsi:.1f}")
                )

            if macd == "Golden Cross":
                alerts.append(
                    (code, "GOLDEN_CROSS", f"🟢 {code} Golden Cross terjadi!")
                )
            elif macd == "Death Cross":
                alerts.append(
                    (code, "DEATH_CROSS", f"🔴 {code} Death Cross terjadi!")
                )

            if volume_spike:
                alerts.append(
                    (
                        code,
                        "VOLUME_SPIKE",
                        f"📊 {code} Volume spike {data['volume_ratio']}x rata-rata",
                    )
                )

            if near_resistance:
                alerts.append(
                    (
                        code,
                        "NEAR_RESISTANCE",
                        f"📈 {code} Mendekati resistance Rp{data['resistance']:,.0f}",
                    )
                )

            if near_support:
                alerts.append(
                    (
                        code,
                        "NEAR_SUPPORT",
                        f"📉 {code} Mendekati support Rp{data['support']:,.0f}",
                    )
                )

        except Exception as e:
            print(f"  ✗ Error checking {code}: {e}")

    # Save alerts to DB
    telegram_ids = crud.get_telegram_ids()
    for code, alert_type, message in alerts:
        for tid in telegram_ids:
            user = crud.get_user(tid)
            if user:
                crud.save_alert(user["id"], code, alert_type, message)

    if alerts:
        print(f"  ✓ {len(alerts)} alerts generated")
    else:
        print(f"  ✓ No alerts")


async def send_telegram_alerts():
    from app.telegram.bot import TelegramBot

    bot = TelegramBot()
    if not bot.token:
        return

    # Initialize application if not already running
    if not bot.app:
        bot.app = (
            Application.builder().token(bot.token).build()
        )

    alerts = crud.get_alerts(limit=10)
    telegram_ids = crud.get_telegram_ids()

    for alert in alerts:
        for tid in telegram_ids:
            try:
                await bot.app.bot.send_message(
                    chat_id=tid,
                    text=f"🔔 *Alert Saham*\n{alert['message']}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"  ✗ Failed to send alert to {tid}: {e}")


def run_send_telegram_alerts():
    asyncio.run(send_telegram_alerts())


def evaluate_predictions_task():
    engine = LearningEngine()
    result = engine.evaluate_predictions(eval_days=7)
    if result.get("evaluated", 0) > 0:
        print(f"  ✓ Evaluated {result['evaluated']} predictions")
        adj_result = engine.adjust_weights_auto()
        if adj_result.get("adjusted"):
            print(f"  ✓ Weights adjusted: {adj_result.get('adjustments', {})}")
