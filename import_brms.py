import json, os, sys
import mysql.connector

STOCK = 'BRMS'
FROM = '2026-07-08'
TO = '2026-08-03'
RAW = os.path.join(os.path.dirname(__file__), 'data', 'raw', 'brms_ajaib_20260708_20260803.json')
IS_GROSS = 0  # match existing convention (net/aggregate basis)

conn = mysql.connector.connect(host='localhost', user='root', password='', database='analisa_saham')
cur = conn.cursor()

with open(RAW) as f:
    data = json.load(f)['result']

rows = []
for side, key in (('buy', 'summary_buy'), ('sell', 'summary_sell')):
    for b in data[key]:
        broker = b['broker']
        rows.append((
            STOCK, FROM, TO, IS_GROSS, broker['code'], side,
            int(b['lot']), float(b['value']), float(b['avg']), 0.0
        ))

cur.execute("DELETE FROM broker_summary WHERE stock_code=%s AND period_from=%s AND period_to=%s", (STOCK, FROM, TO))
sql = """INSERT INTO broker_summary
    (stock_code, period_from, period_to, is_gross, broker_code, side, lots, value, avg_price, net_value)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
cur.executemany(sql, rows)
conn.commit()

cur.execute("SELECT side, COUNT(*), SUM(lots), SUM(value) FROM broker_summary WHERE stock_code=%s GROUP BY side", (STOCK,))
print(f"Inserted {len(rows)} rows for {STOCK} [{FROM}..{TO}]")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} brokers, {r[2]} lots, Rp{r[3]:,.0f}")
conn.close()