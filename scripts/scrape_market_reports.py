import re
import json
import os
import sys
import asyncio
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession

# === CONFIG ===
API_ID = 37884291
API_HASH = '988f336fb2034fefe700fc6cdf4f3513'
CHANNEL = '@creativetrader'
SESSION_FILE = 'telegram_session_string.txt'
OUTPUT_FILE = 'market_reports.json'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_session() -> str:
    if not os.path.exists(SESSION_FILE):
        print('❌ Session file not found')
        return None
    with open(SESSION_FILE, 'r') as f:
        return f.read().strip()


def parse_value_m(text: str) -> float:
    """Parse values like 21.4M, 1.37 Triliun, 863.8 Miliar, 509.03M"""
    text = text.strip().upper().replace(',', '')

    mult = 1
    if 'TRILIUN' in text or 'T' in text.replace(' ', '')[-1:]:
        mult = 1_000_000_000_000
        text = text.replace('TRILIUN', '').replace('T', '')
    elif 'MILIAR' in text or 'B' in text.replace(' ', '')[-1:]:
        mult = 1_000_000_000
        text = text.replace('MILIAR', '').replace('B', '')
    elif 'JUTA' in text:
        mult = 1_000_000
        text = text.replace('JUTA', '')
    elif text[-1] == 'M':
        # In Indonesian market reports, M = Miliar (1e9), not Million (1e6)
        mult = 1_000_000_000
        text = text[:-1]

    # Extract number
    nums = re.findall(r'[\d.]+', text)
    if nums:
        try:
            return float(nums[0]) * mult
        except ValueError:
            return 0
    return 0


def parse_market_report(text: str, msg_date=None) -> dict:
    """Parse @creativetrader market report message."""
    if not text:
        return None

    lines = text.split('\n')
    first = lines[0].strip()

    # Must be a market report
    if 'Market Report' not in first:
        return None
    if 'Top Foreign' not in text and 'Top Local' not in text:
        return None

    report = {
        'date': msg_date.strftime('%Y-%m-%d') if msg_date else None,
        'type': 'akhir_sesi' if 'akhir' in first.lower() else 'sesi1',
        'ihsg_change': None,
        'foreign_buy': [],
        'local_buy': [],
        'gainer': [],
        'loser': [],
        'title': first,
        'content': text,
    }

    # --- IHSG ---
    # "IHSG mengalami penurunan -4.2%" or "IHSG mengalami kenaikan 1.11%"
    ihsg_m = re.search(r'IHSG\s+mengalami\s+(penurunan|kenaikan)\s*(-?[\d,.]+)\s*%', text, re.IGNORECASE)
    if ihsg_m:
        val = float(ihsg_m.group(2).replace(',', '.'))
        if ihsg_m.group(1).lower() == 'penurunan':
            val = -abs(val)
        report['ihsg_change'] = val

    # --- Parse sections ---
    section = None  # foreign_buy, local_buy, gainer, loser
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        lower = stripped.lower()

        if 'top foreign buy' in lower:
            section = 'foreign_buy'
            continue
        elif 'top local buy' in lower:
            section = 'local_buy'
            continue
        elif 'top gainer' in lower:
            section = 'gainer'
            continue
        elif 'top loser' in lower:
            section = 'loser'
            continue
        elif stripped.startswith('Market Report') or stripped.startswith('IHSG') or 'www.creative' in lower:
            continue

        # Parse stock line: "WIFI, 21.4M" or "BBCA, 21.4M"
        if section in ('foreign_buy', 'local_buy'):
            m = re.match(r'([A-Z]+)\s*,\s*([\d.,]+\s*[TBMKbmt]?)', stripped, re.IGNORECASE)
            if m:
                stock = m.group(1).upper().strip()
                # Filter out non-stock codes
                if len(stock) >= 2 and len(stock) <= 5 and not stock.isdigit():
                    value = parse_value_m(m.group(2))
                    if value > 0:
                        report[section].append({'stock': stock, 'value': value})
                        continue

        # Parse gainer/loser: "MUTU, 14.7%" or "WIFI,-15%"
        if section in ('gainer', 'loser'):
            m = re.match(r'([A-Z]+)\s*,?\s*(-?[\d,.]+)\s*%', stripped)
            if m:
                stock = m.group(1).upper().strip()
                pct = float(m.group(2).replace(',', '.'))
                if len(stock) >= 2 and len(stock) <= 5:
                    report[section].append({'stock': stock, 'change_pct': pct})
                    continue

        # If we're in a section but line doesn't match, it might be a continuation or end
        # Don't break - some messages have extra text between sections

    return report


def load_existing_reports() -> list:
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []


def save_reports(reports: list):
    # Sort by date descending
    reports.sort(key=lambda r: r.get('date', ''), reverse=True)
    # Remove duplicates (by date)
    seen = set()
    unique = []
    for r in reports:
        d = r.get('date', '')
        if d and d not in seen:
            seen.add(d)
            unique.append(r)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f'✅ Saved {len(unique)} reports to {OUTPUT_FILE}')


async def fetch_reports(client: TelegramClient, since_date: str = None) -> list:
    channel = await client.get_entity(CHANNEL)
    reports = load_existing_reports()
    existing_dates = {r.get('date') for r in reports if r.get('date')}

    limit_date = None
    if since_date:
        try:
            limit_date = datetime.strptime(since_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    new_count = 0
    skipped = 0
    async for msg in client.iter_messages(channel, limit=500):
        if not msg.text:
            continue
        if limit_date and msg.date and msg.date < limit_date:
            break

        parsed = parse_market_report(msg.text, msg.date)
        if not parsed:
            continue

        d = parsed['date']
        if d and d in existing_dates:
            skipped += 1
            continue

        reports.append(parsed)
        existing_dates.add(d)
        new_count += 1
        print(f'  + {d}: ihsg={parsed["ihsg_change"]} fb={len(parsed["foreign_buy"])} lb={len(parsed["local_buy"])}')

    print(f'\n📋 New: {new_count}, Skipped: {skipped}, Total: {len(reports)}')
    return reports


async def main():
    session_str = load_session()
    if not session_str:
        print('❌ Session file not found. Run: python scripts/auth_telethon.py')
        return

    since = None
    if len(sys.argv) > 1 and sys.argv[1]:
        since = sys.argv[1].strip()

    async with TelegramClient(StringSession(session_str), API_ID, API_HASH) as client:
        me = await client.get_me()
        print(f'✅ Logged in as {me.first_name} (@{me.username})')
        print(f'📡 Scraping {CHANNEL}...')

        # Decide mode: if since given -> incremental; else if output exists -> incremental; else full
        if since:
            mode = 'incremental'
        elif os.path.exists(OUTPUT_FILE):
            mode = 'incremental'
        else:
            mode = 'full'

        if mode == 'full':
            # Remove existing reports and re-scrape fresh
            if os.path.exists(OUTPUT_FILE):
                os.remove(OUTPUT_FILE)
                print('🗑️  Removed existing market_reports.json for fresh scrape')
            reports = await fetch_reports(client, since_date=since)
        else:
            reports = await fetch_reports(client, since_date=since)

        save_reports(reports)

        # Summary
        dates = sorted([r['date'] for r in reports if r.get('date')])
        stocks = set()
        for r in reports:
            for s in r.get('foreign_buy', []):
                stocks.add(s['stock'])
            for s in r.get('local_buy', []):
                stocks.add(s['stock'])
        ihsg_vals = [r['ihsg_change'] for r in reports if r.get('ihsg_change') is not None]

        print(f'\n📊 Summary:')
        print(f'  Reports: {len(reports)}')
        if dates:
            print(f'  Range: {dates[-1]} → {dates[0]}')
        print(f'  Stocks tracked: {len(stocks)}')
        if ihsg_vals:
            print(f'  IHSG: min={min(ihsg_vals):.2f}% max={max(ihsg_vals):.2f}%')
        print(f'  File: {OUTPUT_FILE}')


if __name__ == '__main__':
    asyncio.run(main())
