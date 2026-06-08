"""
Cron job: scrape market reports from @creativetrader → save JSON → import MySQL.
Run daily after market close (16:30 WIB = 09:30 UTC).
"""
import os, sys, subprocess, json
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPER = os.path.join(BASE, 'scripts', 'scrape_market_reports.py')
IMPORTER = os.path.join(BASE, 'scripts', 'import_reports_to_db.py')
REPORT_FILE = os.path.join(BASE, 'market_reports.json')
SESSION_FILE = os.path.join(BASE, 'telegram_session_string.txt')
PYTHON = r'C:\laragon\bin\python\python-3.10\python.exe'

os.chdir(BASE)
TZ_OFFSET = 7  # WIB


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {msg}')


def run_py(script, args=None):
    cmd = [PYTHON, script]
    if args:
        cmd.extend(args)
    log(f'Running: {" ".join(cmd)}')
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log(f'❌ FAILED (exit={r.returncode}): {r.stderr[:500]}')
    else:
        log(f'✅ OK: {r.stdout.strip()[-200:]}')
    return r.returncode


def main():
    log(f'=== Market Report Cron: {datetime.now().strftime("%Y-%m-%d")} ===')

    # Check session
    if not os.path.exists(SESSION_FILE):
        log('❌ Session file missing — cannot scrape')
        return 1

    # Step 1: Scrape new reports
    log('📡 Step 1: Scraping @creativetrader...')
    rc = run_py(SCRAPER)
    if rc != 0:
        log('❌ Scrape failed — check Telethon session validity')
        return rc

    # Step 2: Import to MySQL
    if os.path.exists(REPORT_FILE):
        log('🗄️  Step 2: Importing to MySQL...')
        run_py(IMPORTER)
    else:
        log('⚠️  No market_reports.json found, skipping import')

    # Step 3: Summary
    if os.path.exists(REPORT_FILE):
        try:
            with open(REPORT_FILE) as f:
                data = json.load(f)
            dates = [r['date'] for r in data if r.get('date')]
            log(f'📊 Summary: {len(data)} reports, {len(set(dates))} dates')
            if dates:
                log(f'   Range: {min(dates)} → {max(dates)}')
            stocks = set()
            for r in data:
                for s in r.get('foreign_buy', []):
                    stocks.add(s['stock'])
            log(f'   Stocks tracked: {len(stocks)}')
        except Exception as e:
            log(f'⚠️  Error reading summary: {e}')

    log('✅ Cron job complete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
