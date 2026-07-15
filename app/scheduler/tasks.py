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

            # Only actionable BUY signals
            if rsi_status == "Oversold":
                key = f"{code}_RSI_OVERSOLD"
                if not crud.alert_sent_today(code, "RSI_OVERSOLD"):
                    alerts.append(
                        (code, "RSI_OVERSOLD", f"⚡️ {code} RSI Oversold: {rsi:.1f} — potensi bounce 🚀")
                    )

            if macd == "Golden Cross":
                key = f"{code}_GOLDEN_CROSS"
                if not crud.alert_sent_today(code, "GOLDEN_CROSS"):
                    alerts.append(
                        (code, "GOLDEN_CROSS", f"🟢 {code} Golden Cross — sinyal beli! 🚀")
                    )

            if volume_spike:
                key = f"{code}_VOLUME_SPIKE"
                if not crud.alert_sent_today(code, "VOLUME_SPIKE"):
                    alerts.append(
                        (
                            code,
                            "VOLUME_SPIKE",
                            f"📊 {code} Volume spike {data['volume_ratio']}x rata-rata — akumulasi?",
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
    if not alerts:
        return

    telegram_ids = crud.get_telegram_ids()
    sent_ids = []

    for alert in alerts:
        for tid in telegram_ids:
            try:
                await bot.app.bot.send_message(
                    chat_id=tid,
                    text=f"🔔 *Alert Saham*\n{alert['message']}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"  ✗ Failed to send alert {alert.get('id')} to {tid}: {e}")
        sent_ids.append(alert["id"])

    # Mark as sent so they won't repeat
    if sent_ids:
        crud.mark_alerts_sent(sent_ids)
        print(f"  ✓ {len(sent_ids)} alerts sent and marked as delivered")


def run_send_telegram_alerts():
    asyncio.run(send_telegram_alerts())


def send_evening_reminder():
    """Send 20:30 reminder for next-day prep."""
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    from telegram import Bot
    import asyncio

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id_raw = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id_raw:
        print("  ✗ Evening reminder: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    try:
        chat_id = int(chat_id_raw.strip())
    except ValueError:
        print(f"  ✗ Evening reminder: invalid TELEGRAM_CHAT_ID: {chat_id_raw}")
        return

    text = """📋 *PERSIAPAN BESOK (20:30)*

1\u20e3 Import data broker yg belum masuk (RSC file)
2\u20e3 Cek notifikasi jadwal rilis data baru
3\u20e3 Backup ringan (opsional)
4\u20e3 Pastikan AlphaTracker + semua cron aktif

\u23f0 Besok jadwal: ulang rutinitas yg sama \U0001f305"""

    async def _send():
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

    try:
        asyncio.run(_send())
        print(f"  ✓ Evening reminder sent to {chat_id}")
    except Exception as e:
        print(f"  ✗ Evening reminder send failed: {e}")


def evaluate_predictions_task():
    engine = LearningEngine()
    result = engine.evaluate_predictions(eval_days=7)
    if result.get("evaluated", 0) > 0:
        print(f"  ✓ Evaluated {result['evaluated']} predictions")
        adj_result = engine.adjust_weights_auto()
        if adj_result.get("adjusted"):
            print(f"  ✓ Weights adjusted: {adj_result.get('adjustments', {})}")


def bpjs_daily_scan():
    """Run after market close (~16:00) to pre-scan BPJS candidates for next day."""
    from app.ai.strategies.bpjs_strategy import BPJSStrategy

    print(f"  ✓ BPJS daily scan started: {datetime.now().strftime('%H:%M:%S')}")
    try:
        candidates_list, data_date = BPJSStrategy().scan_candidates()
        if candidates_list:
            print(f"  ✓ Found {len(candidates_list)} BPJS candidates (data: {data_date or '?'})")
            telegram_ids = crud.get_telegram_ids()
            for tid in telegram_ids:
                user = crud.get_user(tid)
                if user:
                    for c in candidates_list[:5]:
                        action = c.get("action", "WAIT")
                        if action == "ENTER":
                            crud.save_alert(
                                user["id"],
                                c["stock_code"],
                                "BPJS_CANDIDATE",
                                f"🎯 BPJS Candidate: {c['stock_code']} - Confidence: {c.get('confidence', 0)}%",
                            )
            print(f"  ✓ BPJS alerts saved for {len(telegram_ids)} users")
        else:
            print(f"  ✓ No BPJS candidates found")
    except Exception as e:
        print(f"  ✗ BPJS daily scan error: {e}")


def longterm_daily_scan():
    """Daily scan for long term candidates after market close."""
    from app.ai.strategies.creative_trader_strategy import CreativeTraderStrategy

    print(f"  ✓ Long Term scan started: {datetime.now().strftime('%H:%M:%S')}")
    try:
        candidates = CreativeTraderStrategy().scan_for_long_term_candidates()
        if candidates:
            print(f"  ✓ Found {len(candidates)} long term candidates")
            telegram_ids = crud.get_telegram_ids()
            for tid in telegram_ids:
                user = crud.get_user(tid)
                if user:
                    for c in candidates[:5]:
                        crud.save_alert(
                            user["id"],
                            c["stock_code"],
                            "LONGTERM_CANDIDATE",
                            f"💎 Long Term: {c['stock_code']} - Fase: {c.get('phase', '')} - Confidence: {c.get('confidence', 0):.0f}%"
                        )
            print(f"  ✓ Long term alerts saved")
        else:
            print(f"  ✓ No long term candidates found")
    except Exception as e:
        print(f"  ✗ Long term scan error: {e}")
