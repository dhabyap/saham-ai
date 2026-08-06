#!/usr/bin/env python3
"""
import_ajaib_to_db.py — Import Ajaib broker-summary JSON into SQLite DB.

Usage:
    python import_ajaib_to_db.py                    # import all files in data/raw/
    python import_ajaib_to_db.py TINS BULL           # import specific stocks
    python import_ajaib_to_db.py --fetch TINS 01-08-2026 04-08-2026  # fetch from Ajaib API
"""

import json, os, sys, sqlite3, urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE, '..', 'data', 'raw')
DB = os.path.join(BASE, '..', 'app', 'database', 'stock.db')


def parse_ajaib_json(data, stock_code=None):
    """Parse Ajaib broker-summary response → list of dicts for DB insert."""
    result = data.get('result', {})
    buy_list = result.get('summary_buy', [])
    sell_list = result.get('summary_sell', [])

    if not stock_code:
        # try to extract from URL or data
        stock_code = data.get('_stock_code', 'UNKNOWN')

    # extract dates from URL if present, else use current
    period_from = data.get('_period_from', datetime.now().strftime('%Y-%m-%d'))
    period_to = data.get('_period_to', datetime.now().strftime('%Y-%m-%d'))

    rows = []
    for entry in buy_list:
        broker = entry.get('broker', {})
        rows.append({
            'stock_code': stock_code,
            'period_from': period_from,
            'period_to': period_to,
            'broker_code': broker.get('code', ''),
            'broker_name': broker.get('name', ''),
            'category': broker.get('category', ''),
            'side': 'buy',
            'lots': abs(int(entry.get('lot', 0))),
            'value': float(entry.get('value', 0)),
            'avg_price': float(entry.get('avg', 0)),
        })

    for entry in sell_list:
        broker = entry.get('broker', {})
        rows.append({
            'stock_code': stock_code,
            'period_from': period_from,
            'period_to': period_to,
            'broker_code': broker.get('code', ''),
            'broker_name': broker.get('name', ''),
            'category': broker.get('category', ''),
            'side': 'sell',
            'lots': abs(int(entry.get('lot', 0))),
            'value': float(entry.get('value', 0)),
            'avg_price': float(entry.get('avg', 0)),
        })

    return rows


def import_to_db(rows):
    """Insert rows into both broker_summary and broker_data tables."""
    if not rows:
        return 0, 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    stock = rows[0]['stock_code']
    period_from = rows[0]['period_from']
    period_to = rows[0]['period_to']

    # delete old data for same stock + period (upsert)
    c.execute("DELETE FROM broker_summary WHERE stock_code=? AND period_from=? AND period_to=?",
              (stock, period_from, period_to))
    c.execute("DELETE FROM broker_data WHERE ticker=? AND from_date=? AND to_date=?",
              (stock, period_from, period_to))

    count_summary = 0
    count_data = 0

    for r in rows:
        # broker_summary
        c.execute("""INSERT INTO broker_summary
            (stock_code, period_from, period_to, is_gross, broker_code, side, lots, value, avg_price)
            VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)""",
            (r['stock_code'], r['period_from'], r['period_to'],
             r['broker_code'], r['side'], r['lots'], r['value'], r['avg_price']))
        count_summary += 1

        # broker_data
        c.execute("""INSERT INTO broker_data
            (ticker, from_date, to_date, broker_code, broker_name, category, direction, lots, value, avg_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (r['stock_code'], r['period_from'], r['period_to'],
             r['broker_code'], r['broker_name'], r['category'],
             r['side'], r['lots'], r['value'], r['avg_price']))
        count_data += 1

    conn.commit()
    conn.close()
    return count_summary, count_data


def load_raw_file(filepath):
    """Load Ajaib JSON file, extract stock code and dates from filename or URL."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # try to extract stock code from filename: brms_ajaib_20260708_20260803.json
    fname = os.path.basename(filepath)
    stock = None
    pf = pt = None

    # filename pattern: <stock>_ajaib_<from>_<to>.json
    parts = fname.replace('.json', '').split('_')
    if len(parts) >= 4 and parts[1] == 'ajaib':
        stock = parts[0].upper()
        pf_raw, pt_raw = parts[2], parts[3]
        try:
            pf = f"{pf_raw[:4]}-{pf_raw[4:6]}-{pf_raw[6:8]}"
            pt = f"{pt_raw[:4]}-{pt_raw[4:6]}-{pt_raw[6:8]}"
        except Exception:
            pass

    # also check cached doc files
    if not stock and 'doc_' in fname:
        # need to detect from content or URL
        pass

    # try to extract from embedded URL
    if not stock:
        # look for stock in result keys or check if there's URL metadata
        pass

    # fallback: detect stock from first buy entry name patterns
    if not stock:
        # check _stock_code set externally
        stock = data.get('_stock_code', fname.split('_')[0].upper()[:4])

    data['_stock_code'] = stock
    data['_period_from'] = pf or '2026-06-08'
    data['_period_to'] = pt or '2026-08-03'

    return data


def fetch_ajaib(stock, start_date, end_date):
    """Fetch broker summary from Ajaib API."""
    url = f"https://ht2.ajaib.co.id/api/v1/stock/data/stock/{stock}/broker-summary/?start_date={start_date}&end_date={end_date}&net=true"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())

    # save raw
    os.makedirs(RAW_DIR, exist_ok=True)
    raw_file = os.path.join(RAW_DIR, f"{stock.lower()}_ajaib_{start_date.replace('-', '')}_{end_date.replace('-', '')}.json")
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    data['_stock_code'] = stock
    data['_period_from'] = start_date
    data['_period_to'] = end_date
    return data


def main():
    stocks_to_fetch = []

    # parse args
    if '--fetch' in sys.argv:
        idx = sys.argv.index('--fetch')
        stock = sys.argv[idx + 1].upper() if idx + 1 < len(sys.argv) else None
        pf = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else '2026-01-01'
        pt = sys.argv[idx + 3] if idx + 3 < len(sys.argv) else datetime.now().strftime('%Y-%m-%d')
        if stock:
            stocks_to_fetch.append((stock, pf, pt))

    # specific stocks
    specific = [a.upper() for a in sys.argv[1:] if not a.startswith('--') and len(a) <= 6]

    # gather all raw files
    all_files = []
    if os.path.exists(RAW_DIR):
        for f in sorted(os.listdir(RAW_DIR)):
            if f.endswith('.json') and 'ajaib' in f.lower():
                all_files.append(os.path.join(RAW_DIR, f))

    # add cached docs
    cache_dir = os.path.expanduser(r'~\AppData\Local\hermes\cache\documents')
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            if f.endswith('.txt') or f.endswith('.json'):
                fp = os.path.join(cache_dir, f)
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        d = json.load(fh)
                    if 'err_code' in d or 'result' in d:
                        all_files.append(fp)
                except Exception:
                    pass

    total_summary = 0
    total_data = 0
    processed = set()

    print(f"Found {len(all_files)} raw files + {len(stocks_to_fetch)} API fetches\n")

    for filepath in all_files:
        try:
            data = load_raw_file(filepath)
            stock = data.get('_stock_code', 'UNKNOWN')

            if specific and stock not in specific:
                continue
            if stock in processed:
                continue

            rows = parse_ajaib_json(data, stock)
            if not rows:
                print(f"  SKIP {stock}: no rows parsed")
                continue

            s, d = import_to_db(rows)
            total_summary += s
            total_data += d
            processed.add(stock)
            print(f"  OK {stock:8} {s:4} rows summary + {d:4} rows data  [{data['_period_from']} → {data['_period_to']}]")
        except Exception as e:
            print(f"  ERR {os.path.basename(filepath)}: {e}")

    for stock, pf, pt in stocks_to_fetch:
        if stock in processed:
            continue
        try:
            print(f"  Fetching {stock} from Ajaib API...")
            data = fetch_ajaib(stock, pf, pt)
            rows = parse_ajaib_json(data, stock)
            s, d = import_to_db(rows)
            total_summary += s
            total_data += d
            processed.add(stock)
            print(f"  OK {stock:8} {s:4} rows summary + {d:4} rows data  [{pf} → {pt}]")
        except Exception as e:
            print(f"  ERR {stock}: {e}")

    print(f"\n=== DONE: {len(processed)} stocks, {total_summary} summary + {total_data} data rows ===")


if __name__ == '__main__':
    main()
