#!/usr/bin/env python3
"""
import_all_to_mysql.py — Import SEMUA data broker ke MySQL (Laragon analisa_saham).

Sumber data:
  1. data/raw/*_ajaib_*.json — file hasil scrape Ajaib (BRMS, BRPT, BULL, TINS, HMSP)
  2. SQLite stock.db broker_summary — data lama yang mungkin cuma ada di SQLite

Target: MySQL analisa_saham.broker_summary (+ broker_meta untuk overview/distribution)

Idempotent: UNIQUE(stock_code, period_from, period_to, broker_code, side)
            -> INSERT ... ON DUPLICATE KEY UPDATE
"""

import json, os, sys, sqlite3

# ============ CONFIG ============
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT, 'data', 'raw')
SQLITE_DB = os.path.join(PROJECT, 'app', 'database', 'stock.db')

MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASS = '127.0.0.1', 3306, 'root', ''
MYSQL_DB = 'analisa_saham'

def mysql_conn():
    import mysql.connector
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASS, database=MYSQL_DB, autocommit=False
    )

# ============ PARSING ============

def parse_ajaib(data, stock, period_from, period_to):
    """Ajaib JSON -> rows (stock, from, to, broker, side, lots, value, avg, net)."""
    rows = []
    result = data.get('result', {})
    overview = result.get('overview', {})
    for side in ('buy', 'sell'):
        for entry in result.get(f'summary_{side}', []):
            broker = entry.get('broker', {})
            rows.append({
                'stock_code': stock,
                'period_from': period_from,
                'period_to': period_to,
                'broker_code': broker.get('code', ''),
                'side': side,
                'lots': abs(int(entry.get('lot', 0))),
                'value': float(entry.get('value', 0)),
                'avg_price': float(entry.get('avg', 0)),
                'net_value': 0.0,
            })
    return rows, overview

def parse_raw_file(path):
    """Parse file data/raw/*_ajaib_*.json -> (stock, rows, overview, from, to)."""
    fname = os.path.basename(path)
    parts = fname.replace('.json', '').split('_')
    # format: <stock>_ajaib_<YYYYMMDD>_<YYYYMMDD>.json
    if len(parts) >= 4 and parts[1] == 'ajaib':
        stock = parts[0].upper()
        try:
            pf = f"{parts[2][:4]}-{parts[2][4:6]}-{parts[2][6:8]}"
            pt = f"{parts[3][:4]}-{parts[3][4:6]}-{parts[3][6:8]}"
        except Exception:
            pf = pt = None
    else:
        stock, pf, pt = None, None, None

    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not stock:
        return None
    rows, overview = parse_ajaib(data, stock, pf, pt)
    return stock, rows, overview, pf, pt

def parse_sqlite_broker_summary():
    """Baca semua baris broker_summary dari SQLite (data lama)."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT stock_code, period_from, period_to, broker_code, side,
               lots, value, avg_price
        FROM broker_summary
    """).fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            'stock_code': r['stock_code'],
            'period_from': r['period_from'],
            'period_to': r['period_to'],
            'broker_code': r['broker_code'],
            'side': r['side'],
            'lots': int(r['lots'] or 0),
            'value': float(r['value'] or 0),
            'avg_price': float(r['avg_price'] or 0),
            'net_value': 0.0,
        })
    return out

# ============ INSERT ============

def insert_mysql(rows):
    """Bulk insert ke MySQL, upsert on duplicate."""
    if not rows:
        return 0
    conn = mysql_conn()
    cur = conn.cursor()
    sql = """
        INSERT INTO broker_summary
            (stock_code, period_from, period_to, is_gross, broker_code, side,
             lots, value, avg_price, net_value)
        VALUES (%s, %s, %s, 0, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            lots = VALUES(lots),
            value = VALUES(value),
            avg_price = VALUES(avg_price),
            net_value = VALUES(net_value)
    """
    batch = []
    for r in rows:
        batch.append((
            r['stock_code'], r['period_from'], r['period_to'], r['broker_code'],
            r['side'], r['lots'], r['value'], r['avg_price'], r['net_value']
        ))
    cur.executemany(sql, batch)
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n

# ============ MAIN ============

def main():
    import mysql.connector
    try:
        conn = mysql_conn()
        conn.close()
    except Exception as e:
        print(f"ERROR: MySQL tidak bisa connect: {e}")
        print("Pastikan Laragon MySQL jalan (Start All -> MySQL).")
        sys.exit(1)

    all_rows = []
    sources = []

    # 1. Raw files Ajaib
    if os.path.exists(RAW_DIR):
        for f in sorted(os.listdir(RAW_DIR)):
            if f.endswith('.json') and 'ajaib' in f:
                try:
                    parsed = parse_raw_file(os.path.join(RAW_DIR, f))
                    if parsed:
                        stock, rows, overview, pf, pt = parsed
                        all_rows.extend(rows)
                        sources.append(f"{stock} (raw {pf}→{pt}, {len(rows)} rows)")
                except Exception as e:
                    print(f"  SKIP {f}: {e}")

    # 2. SQLite legacy
    try:
        legacy = parse_sqlite_broker_summary()
        all_rows.extend(legacy)
        sources.append(f"SQLite legacy ({len(legacy)} rows)")
    except Exception as e:
        print(f"  SKIP SQLite: {e}")

    # dedup by (stock, from, to, broker, side) — raw wins, legacy backs
    seen = {}
    for r in all_rows:
        key = (r['stock_code'], r['period_from'], r['period_to'], r['broker_code'], r['side'])
        # prefer raw (last in list = legacy, so raw inserted first wins)
        seen.setdefault(key, r)

    final = list(seen.values())
    print(f"Total baris unik: {len(final)} dari {len(all_rows)}")

    # group by stock
    by_stock = {}
    for r in final:
        by_stock.setdefault(r['stock_code'], []).append(r)

    print("\n=== Import per saham ke MySQL ===")
    total = 0
    for stock in sorted(by_stock):
        rows = by_stock[stock]
        n = insert_mysql(rows)
        total += n
        pf = rows[0]['period_from']
        pt = rows[0]['period_to']
        print(f"  {stock:6} {len(rows):4} rows  [{pf} → {pt}]")

    print(f"\n=== DONE: {total} baris di MySQL ===")
    print("\nSumber:")
    for s in sources:
        print(f"  - {s}")

if __name__ == '__main__':
    main()
