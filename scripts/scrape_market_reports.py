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
    # Akhir sesi: has Top Foreign / Top Local. Sesi 1: no foreign/local sections.
    is_sesi1 = 'sesi 1' in first.lower() or 'sesi1' in first.lower()
    if not is_sesi1 and 'Top Foreign' not in text and 'Top Local' not in text:
        return None

    report = {
        'date': msg_date.strftime('%Y-%m-%d') if msg_date else None,
        'type': 'akhir_sesi' if 'akhir' in first.lower() else 'sesi1',
        'ihsg_change': None,
        'foreign_buy': [],
        'local_buy': [],
        'gainer': [],
        'loser': [],
        'foreign_buy_yesterday': [],  # sesi1: saham naik setelah asing beli kemarin
        'volume_spike': [],            # sesi1: lonjakan volume
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
        elif 'naik setelah investor asing' in lower or 'naik setelah asing' in lower:
            section = 'foreign_buy_yesterday'
            continue
        elif 'naik setelah turun' in lower:
            section = 'dropped_3days'
            continue
        elif 'lonjakan volume' in lower:
            section = 'volume_spike'
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

        # Parse sesi1: foreign_buy_yesterday — "UNVR 1.2% / 8.8M"
        if section == 'foreign_buy_yesterday':
            m = re.match(r'([A-Z]+)\s+(-?[\d.]+)%\s*/\s*([\d.,]+\s*[TBMKtbmk]?)', stripped)
            if not m:
                # Try alternate: "UNVR 1.2%"
                m = re.match(r'([A-Z]+)\s+(-?[\d.]+)%', stripped)
            if m:
                stock = m.group(1).upper().strip()
                pct = float(m.group(2).replace(',', '.'))
                vol_raw = m.group(3) if len(m.groups()) >= 3 else '0'
                vol = parse_value_m(vol_raw) if vol_raw else 0
                if len(stock) >= 2 and len(stock) <= 5:
                    report['foreign_buy_yesterday'].append({'stock': stock, 'change_pct': pct, 'volume': vol})
                    continue

        # Parse sesi1: volume_spike — "BABY  35x" or "BABY 35X"
        if section == 'volume_spike':
            m = re.match(r'([A-Z]+)\s+([\d.]+)x', stripped, re.IGNORECASE)
            if m:
                stock = m.group(1).upper().strip()
                mult = float(m.group(2))
                if len(stock) >= 2 and len(stock) <= 5:
                    report['volume_spike'].append({'stock': stock, 'multiplier': mult})
                    continue

        # Skip "dropped_3days" section data (usually "-" or empty)
        if section == 'dropped_3days':
            continue

        # If we're in a section but line doesn't match, it might be a continuation or end
        # Don't break - some messages have extra text between sections

    return report


def parse_broker_table(text: str, msg_date=None) -> dict:
    """Parse @creativetrader per-stock broker table post.
    
    Format example:
      SIAPA PENGGORRENG MISTERIUS BBCA ?!
      NBY  NBLot   NBVal    BAvg   |  NSL   NSLot   NSVal    SAvg
      RX   1.0M    533.3B   5,350  |  AK    -2.2M   -1096B   5,110
      BB   781,977 416.0B   5,337  |  ZP    -1.9M   -994.1B  5,198
    """
    if not text:
        return None
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) < 3:
        return None
    
    # Detect stock code from title — "BBCA" in "SIAPA ... BBCA ?!"
    stock_match = re.search(r'\b([A-Z]{2,4})\b', lines[0])
    if not stock_match:
        return None
    stock_code = stock_match.group(1)
    # Skip if looks like common words
    if stock_code in ('SIAPA', 'PENGGORRENG', 'MISTERIUS'):
        stocks = re.findall(r'\b[A-Z]{2,4}\b', lines[0])
        stock_code = stocks[-1] if stocks else None
    if not stock_code or len(stock_code) < 2:
        return None
    
    # Find header line — look for NBY / NSL columns
    header_idx = None
    for i, line in enumerate(lines):
        if 'NBY' in line.upper() or 'NBVAL' in line.upper():
            header_idx = i
            break
    if header_idx is None:
        return None
    
    # Parse data rows after header
    buys = []
    sells = []
    for line in lines[header_idx+1:]:
        if not line.strip():
            continue
        # Split by pipe for buy vs sell
        parts = [p.strip() for p in line.split('|')]
        buy_part = parts[0].strip() if len(parts) > 0 else ''
        sell_part = parts[1].strip() if len(parts) > 1 else ''
        
        # Parse buy: "RX 1.0M 533.3B 5,350" or "BB 781,977 416.0B 5,337"
        buy_tokens = buy_part.split()
        if len(buy_tokens) >= 4:
            code = buy_tokens[0].upper()
            if len(code) == 2:  # 2-letter broker code
                try:
                    lot = parse_value_m(buy_tokens[1])
                    val = parse_value_m(buy_tokens[2])
                    avg = float(buy_tokens[3].replace(',', '')) if len(buy_tokens) > 3 else 0
                    buys.append({'broker': code, 'lots': lot, 'value': val, 'avg_price': avg})
                except (ValueError, IndexError):
                    pass
        
        # Parse sell: "AK -2.2M -1096B 5,110"
        sell_tokens = sell_part.split()
        if len(sell_tokens) >= 4:
            code = sell_tokens[0].upper()
            if len(code) == 2:
                try:
                    lot = abs(parse_value_m(sell_tokens[1]))
                    val = abs(parse_value_m(sell_tokens[2]))
                    avg = float(sell_tokens[3].replace(',', '')) if len(sell_tokens) > 3 else 0
                    sells.append({'broker': code, 'lots': lot, 'value': val, 'avg_price': avg})
                except (ValueError, IndexError):
                    pass
    
    if not buys and not sells:
        return None
    
    return {
        'type': 'broker_table',
        'date': msg_date.strftime('%Y-%m-%d') if msg_date else None,
        'stock': stock_code,
        'title': lines[0],
        'content': text,
        'broker_buy': buys,
        'broker_sell': sells,
        'total_buy_val': sum(b['value'] for b in buys),
        'total_sell_val': sum(s['value'] for s in sells),
        'net_val': sum(b['value'] for b in buys) - sum(s['value'] for s in sells),
    }


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
    # Remove duplicates (by date + type, so sesi1 + akhir sesi same day both kept)
    seen = set()
    unique = []
    for r in reports:
        key = f"{r.get('date', '')}_{r.get('type', '')}"
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f'✅ Saved {len(unique)} reports to {OUTPUT_FILE}')

    # Also save to DB
    save_reports_to_db(unique)


def save_reports_to_db(reports: list):
    """Save reports to DB. Tries app helper first (MySQL/SQLite), falls back to stock.db SQLite."""
    try:
        # Load project .env so DATABASE_TYPE is picked up
        dotenv_path = os.path.join(os.path.dirname(BASE_DIR), '.env')
        if os.path.exists(dotenv_path):
            with open(dotenv_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        sys.path.insert(0, os.path.join(BASE_DIR, '..'))
        from app.database.database import save_market_reports_to_db as _save
        _save(reports)
        print(f'✅ Saved {len(reports)} reports to DB')
        return
    except Exception as e:
        print(f'⚠️ App DB helper failed ({e}), falling back to stock.db')

    # Fallback: direct SQLite to stock.db
    db_path = os.path.join(os.path.dirname(BASE_DIR), 'app', 'database', 'stock.db')
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS market_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'akhir_sesi',
                ihsg_change REAL,
                gainer TEXT,
                loser TEXT,
                foreign_buy TEXT,
                local_buy TEXT,
                foreign_buy_yesterday TEXT,
                volume_spike TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, type)
            )
        ''')
        for r in reports:
            cur.execute('''
                INSERT OR REPLACE INTO market_reports
                (date, type, ihsg_change, gainer, loser, foreign_buy, local_buy,
                 foreign_buy_yesterday, volume_spike, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r.get('date'),
                r.get('type', 'akhir_sesi'),
                r.get('ihsg_change'),
                json.dumps(r.get('gainer', [])),
                json.dumps(r.get('loser', [])),
                json.dumps(r.get('foreign_buy', [])),
                json.dumps(r.get('local_buy', [])),
                json.dumps(r.get('foreign_buy_yesterday', [])),
                json.dumps(r.get('volume_spike', [])),
                r.get('content', '')
            ))
        conn.commit()
        print(f'✅ Saved {len(reports)} reports to stock.db ({db_path})')
    except Exception as e:
        print(f'❌ DB save error: {e}')
        conn.rollback()
    finally:
        conn.close()


BROKER_STOCK_DATA_DIR = os.path.join(BASE_DIR, 'broker_tables')
os.makedirs(BROKER_STOCK_DATA_DIR, exist_ok=True)


def _save_broker_table(bt: dict):
    """Save per-stock broker table data."""
    stock = bt['stock']
    date = bt.get('date', 'unknown')
    filepath = os.path.join(BROKER_STOCK_DATA_DIR, f'{stock}_{date}.json')
    with open(filepath, 'w') as f:
        json.dump(bt, f, indent=2, ensure_ascii=False)
    # Also save a running list per stock
    all_file = os.path.join(BROKER_STOCK_DATA_DIR, f'{stock}_all.json')
    all_data = []
    if os.path.exists(all_file):
        try:
            with open(all_file) as f:
                all_data = json.load(f)
        except (json.JSONDecodeError, Exception):
            pass
    # Replace if same date exists, else append
    all_data = [x for x in all_data if x.get('date') != date]
    all_data.append(bt)
    all_data.sort(key=lambda x: x.get('date', ''), reverse=True)
    with open(all_file, 'w') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


async def fetch_reports(client: TelegramClient, since_date: str = None) -> list:
    channel = await client.get_entity(CHANNEL)
    reports = load_existing_reports()
    existing_dates = {(r.get('date'), r.get('type')) for r in reports if r.get('date')}

    limit_date = None
    if since_date:
        try:
            limit_date = datetime.strptime(since_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    new_count = 0
    skipped = 0
    broker_tables = []
    async for msg in client.iter_messages(channel, limit=2000):
        if not msg.text:
            continue
        if limit_date and msg.date and msg.date < limit_date:
            break

        parsed = parse_market_report(msg.text, msg.date)
        if parsed:
            d = parsed['date']
            if d and (d, parsed['type']) in existing_dates:
                skipped += 1
                continue
            reports.append(parsed)
            existing_dates.add(d)
            new_count += 1
            if parsed['type'] == 'sesi1':
                fby = len(parsed.get('foreign_buy_yesterday', []))
                vs = len(parsed.get('volume_spike', []))
                print(f'  + {d}: IHSG={parsed["ihsg_change"]} gainer={len(parsed["gainer"])} fby={fby} vol_spike={vs}')
            else:
                print(f'  + {d}: IHSG={parsed["ihsg_change"]} fb={len(parsed["foreign_buy"])} lb={len(parsed["local_buy"])}')
            continue

        # Try broker table parser
        bt = parse_broker_table(msg.text, msg.date)
        if bt:
            broker_tables.append(bt)
            print(f'  📊 Broker table: {bt["stock"]} ({bt["date"]}) — {len(bt["broker_buy"])} buy, {len(bt["broker_sell"])} sell')
            # Save individual broker data to a per-stock file
            _save_broker_table(bt)

    print(f'📋 New: {new_count}, Skipped: {skipped}, Broker Tables: {len(broker_tables)}, Total: {len(reports)}')
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
        sesi1_count = sum(1 for r in reports if r.get('type') == 'sesi1')
        if sesi1_count:
            print(f'    Sesi 1: {sesi1_count}  |  Akhir sesi: {len(reports) - sesi1_count}')
        if dates:
            print(f'  Range: {dates[-1]} → {dates[0]}')
        print(f'  Stocks tracked: {len(stocks)}')
        if ihsg_vals:
            print(f'  IHSG: min={min(ihsg_vals):.2f}% max={max(ihsg_vals):.2f}%')
        print(f'  File: {OUTPUT_FILE}')


if __name__ == '__main__':
    asyncio.run(main())
