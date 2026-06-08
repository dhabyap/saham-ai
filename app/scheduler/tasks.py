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


def bpjs_daily_scan():
    """Run after market close (~16:00) to pre-scan BPJS candidates for next day."""
    from app.ai.strategies.bpjs_strategy import BPJSStrategy

    print(f"  ✓ BPJS daily scan started: {datetime.now().strftime('%H:%M:%S')}")
    try:
        candidates = BPJSStrategy().scan_candidates()
        if candidates:
            print(f"  ✓ Found {len(candidates)} BPJS candidates")
            telegram_ids = crud.get_telegram_ids()
            for tid in telegram_ids:
                user = crud.get_user(tid)
                if user:
                    for c in candidates[:5]:
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


def seed_initial_airdrops():
    """Seed known airdrops into DB. Safe to call multiple times (upsert)."""
    from app.database import crud as c
    airdrops = [
        {
            "name": "Hyperliquid Season 2",
            "url": "https://app.hyperliquid.xyz",
            "description": "Trade HyperCore, stake HYPE, interact with HyperEVM daily",
            "estimated_value": "$1,000–$10,000+",
            "source": "last30days",
            "platform": "Hyperliquid",
            "requirements": "Trade HyperCore, stake HYPE, interact with HyperEVM",
            "deadline": None,
        },
        {
            "name": "Polymarket $POLY",
            "url": "https://polymarket.com",
            "description": "CMO confirmed token coming. Trade across multiple markets, link X account.",
            "estimated_value": "$200–$2,000",
            "source": "last30days",
            "platform": "Polymarket",
            "requirements": "Trade across markets, link X account",
            "deadline": None,
        },
        {
            "name": "ACI Testnet",
            "url": "https://testnet.aci.com",
            "description": "30M tokens confirmed. Phase 1 ends June 30. Free, swap + stake on Sepolia.",
            "estimated_value": "30M tokens (free)",
            "source": "last30days",
            "platform": "ACI",
            "requirements": "Swap + stake on Sepolia testnet",
            "deadline": "2026-06-30",
        },
        {
            "name": "Pod Network",
            "url": "https://pod.network",
            "description": "Interact with Pod Network",
            "estimated_value": "$500–$5,000",
            "source": "last30days",
            "platform": "Pod",
            "requirements": "TBD - check website",
            "deadline": None,
        },
    ]
    for a in airdrops:
        c.upsert_airdrop(
            name=a["name"],
            url=a["url"],
            description=a["description"],
            estimated_value=a["estimated_value"],
            source=a["source"],
            platform=a["platform"],
            requirements=a["requirements"],
            deadline=a["deadline"],
        )
    print(f"  ✓ Seeded {len(airdrops)} airdrops to DB")


def refresh_airdrops_task():
    """Run last30days engine to refresh airdrop data."""
    import subprocess, json, re, os
    from app.database import crud as c

    print(f"  🔄 Refreshing airdrops: {datetime.now().strftime('%H:%M:%S')}")

    skill_dir = os.path.expandvars("$HERMES_HOME/skills/research/last30days")
    if not os.path.isdir(skill_dir):
        print(f"  ✗ last30days skill not found at {skill_dir}")
        seed_initial_airdrops()
        return

    queries = [
        "crypto airdrop June 2026",
        "best crypto airdrops this week",
    ]

    for query in queries:
        try:
            result = subprocess.run(
                ["python3", "scripts/last30days.py", query, "--days=7", "--search=reddit", "--emit=compact"],
                cwd=skill_dir,
                capture_output=True, text=True, timeout=60,
            )
            # Look for "Best Crypto Airdrops" patterns in output
            output = result.stdout + result.stderr
            name_match = re.findall(r'\*([^*]+)\*\s*\$\d', output)
            url_match = re.findall(r'https?://[^\s\)]+', output)
            if name_match:
                print(f"  ✓ Found {len(name_match)} airdrop mentions via last30days")
        except subprocess.TimeoutExpired:
            print(f"  ✗ last30days timeout for query: {query}")
        except Exception as e:
            print(f"  ✗ last30days error: {e}")

    print(f"  ✓ Airdrop refresh done")
