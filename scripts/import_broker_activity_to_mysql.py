#!/usr/bin/env python3
"""
import_broker_activity_to_mysql.py — Import activity 1 broker (format Ajaib)
ke broker_summary MySQL.

Usage:
  python scripts/import_broker_activity_to_mysql.py <file.json> <BROKER_CODE> <start_date> <end_date>

Format input: Ajaib /api/v1/stock/data/broker/{KODE}/activity
  { "result": { "buy": [{code,value,avg,lot}...], "sell": [...] } }
Idempotent: hapus dulu rows broker+periode yang sama, lalu insert.
"""
import json, sys, os
import mysql.connector

MYSQL = dict(host="127.0.0.1", port=3306, user="root", password="", database="analisa_saham")

def main():
    if len(sys.argv) < 5:
        print("Usage: import_broker_activity_to_mysql.py <file.json> <BROKER_CODE> <start> <end>")
        sys.exit(1)
    path, broker, pf, pt = sys.argv[1], sys.argv[2].upper(), sys.argv[3], sys.argv[4]

    text = open(path, encoding="utf-8").read()
    # strip trailing URL/non-JSON setelah objek
    last = text.rfind("}")
    data = json.loads(text[: last + 1])
    buy = data.get("result", {}).get("buy", [])
    sell = data.get("result", {}).get("sell", [])

    conn = mysql.connector.connect(**MYSQL)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM broker_summary WHERE broker_code=%s AND period_from=%s AND period_to=%s",
        (broker, pf, pt),
    )

    n = 0
    tot_buy = 0
    tot_sell = 0
    for item in buy:
        if not item.get("lot") and not item.get("value"):
            continue
        cur.execute(
            "INSERT INTO broker_summary (stock_code, period_from, period_to, broker_code, side, lots, value, avg_price, net_value, is_gross) "
            "VALUES (%s,%s,%s,%s,'buy',%s,%s,%s,%s,0)",
            (item["code"], pf, pt, broker, item["lot"], item["value"], item["avg"], item["value"]),
        )
        n += 1
        tot_buy += item["value"]
    for item in sell:
        if not item.get("lot") and not item.get("value"):
            continue
        cur.execute(
            "INSERT INTO broker_summary (stock_code, period_from, period_to, broker_code, side, lots, value, avg_price, net_value, is_gross) "
            "VALUES (%s,%s,%s,%s,'sell',%s,%s,%s,%s,0)",
            (item["code"], pf, pt, broker, item["lot"], item["value"], item["avg"], -item["value"]),
        )
        n += 1
        tot_sell += item["value"]
    conn.commit()

    print(f"OK {broker} {pf}->{pt}: {len(buy)} buy + {len(sell)} sell = {n} rows")
    print(f"  total buy  Rp{tot_buy:,.0f}")
    print(f"  total sell Rp{tot_sell:,.0f}")
    print(f"  net        Rp{tot_buy - tot_sell:,.0f}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
