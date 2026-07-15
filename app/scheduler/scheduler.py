from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import Config
from app.scheduler.tasks import (
    check_watchlist_alerts,
    update_market_summary,
    run_send_telegram_alerts,
    evaluate_predictions_task,
    bpjs_daily_scan,
    longterm_daily_scan,
    send_evening_reminder,
)


scheduler = BackgroundScheduler()


def start_scheduler():
    interval = Config.SCHEDULER_INTERVAL

    scheduler.add_job(
        update_market_summary,
        trigger=IntervalTrigger(minutes=interval),
        id="update_market_summary",
        name="Update market summary",
        replace_existing=True,
    )

    scheduler.add_job(
        check_watchlist_alerts,
        trigger=IntervalTrigger(minutes=interval),
        id="check_watchlist_alerts",
        name="Check watchlist alerts",
        replace_existing=True,
    )

    scheduler.add_job(
        run_send_telegram_alerts,
        trigger=IntervalTrigger(minutes=interval),
        id="send_telegram_alerts",
        name="Send Telegram alerts",
        replace_existing=True,
    )

    scheduler.add_job(
        evaluate_predictions_task,
        trigger=IntervalTrigger(minutes=interval * 4),
        id="evaluate_predictions",
        name="Evaluate AI predictions",
        replace_existing=True,
    )

    scheduler.add_job(
        bpjs_daily_scan,
        trigger=CronTrigger(hour=16, minute=5, timezone="Asia/Jakarta"),
        id="bpjs_daily_scan",
        name="BPJS daily scan after market close",
        replace_existing=True,
    )

    scheduler.add_job(
        longterm_daily_scan,
        trigger=CronTrigger(hour=16, minute=10, timezone="Asia/Jakarta"),
        id="longterm_daily_scan",
        name="Long term daily scan",
        replace_existing=True,
    )

    scheduler.add_job(
        send_evening_reminder,
        trigger=CronTrigger(hour=20, minute=30, timezone="Asia/Jakarta"),
        id="send_evening_reminder",
        name="Evening reminder for next-day prep",
        replace_existing=True,
    )

    scheduler.start()
    print(f"⏰ Scheduler started (interval: {interval} minutes)")
    print("  - Market summary update")
    print("  - Watchlist alert check")
    print("  - Telegram alert delivery")
    print("  - AI prediction evaluation")
    print("  - BPJS daily scan (16:05 WIB)")
    print("  - Long term daily scan (16:10 WIB)")
    print("  - Evening reminder (20:30 WIB)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("⏰ Scheduler stopped")
