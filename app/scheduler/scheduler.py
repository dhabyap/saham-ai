from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Config
from app.scheduler.tasks import (
    check_watchlist_alerts,
    update_market_summary,
    run_send_telegram_alerts,
    evaluate_predictions_task,
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

    scheduler.start()
    print(f"⏰ Scheduler started (interval: {interval} minutes)")
    print("  - Market summary update")
    print("  - Watchlist alert check")
    print("  - Telegram alert delivery")
    print("  - AI prediction evaluation")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("⏰ Scheduler stopped")
