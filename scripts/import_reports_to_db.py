"""
Import market_reports.json → MySQL foreign_flow table.
"""
import json
import sys
import os
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'analisa_saham',
}


def import_reports(report_file: str, clear_first: bool = True):
    if not os.path.exists(report_file):
        print(f'❌ File not found: {report_file}')
        return 0, 0

    with open(report_file, 'r') as f:
        reports = json.load(f)

    print(f'📖 Loaded {len(reports)} reports')
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    if clear_first:
        cur.execute('DELETE FROM foreign_flow')
        conn.commit()
        print('🗑️  Cleared existing foreign_flow')

    stocks_imported = 0
    dates_imported = 0

    for report in reports:
        date = report.get('date')
        if not date:
            continue

        # Foreign buy
        for item in report.get('foreign_buy', []):
            stock = item['stock']
            value = item['value']
            cur.execute(
                'INSERT IGNORE INTO foreign_flow (stock_code, trade_date, foreign_buy, foreign_sell, foreign_net, domestic_buy, domestic_sell, total_volume, source, created_at) '
                'VALUES (%s, %s, %s, 0, %s, 0, 0, %s, %s, NOW())',
                (stock, date, value, value, value, 'creativetrader')
            )
            stocks_imported += 1

        # Local buy
        for item in report.get('local_buy', []):
            stock = item['stock']
            value = item['value']
            cur.execute(
                'INSERT IGNORE INTO foreign_flow (stock_code, trade_date, foreign_buy, foreign_sell, foreign_net, domestic_buy, domestic_sell, total_volume, source, created_at) '
                'VALUES (%s, %s, 0, %s, %s, %s, 0, %s, %s, NOW())',
                (stock, date, value, -value, value, value, 'creativetrader')
            )
            stocks_imported += 1

        dates_imported += 1

    conn.commit()
    cur.execute('SELECT COUNT(*) FROM foreign_flow')
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT trade_date) FROM foreign_flow')
    dates = cur.fetchone()[0]
    conn.close()

    return dates_imported, stocks_imported, total, dates


if __name__ == '__main__':
    report_file = sys.argv[1] if len(sys.argv) > 1 else 'market_reports.json'
    clear = '--keep' not in sys.argv

    d, s, total, total_dates = import_reports(report_file, clear_first=clear)
    print(f'✅ Imported: {d} dates, {s} stock-rows')
    print(f'📊 foreign_flow now: {total} rows, {total_dates} distinct dates')
