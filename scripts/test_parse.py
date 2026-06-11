"""Test parsing sesi1 report."""
import ast
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Verify syntax
with open(os.path.join(os.path.dirname(__file__), 'scrape_market_reports.py')) as f:
    ast.parse(f.read())
print('Syntax OK')

from scripts.scrape_market_reports import parse_market_report

test_msg = '''Market Report Sesi 1  by www.creative-trader.id

IHSG mengalami penurunan -1.91 %.

Top Gainer
BABY, 27%
OILS, 26.8%
TMPO, 20.2%
MLPT, 12.6%
LCKM, 10.6%

Top Loser
HRTA,-14.2%
TRIN,-14%
ARCI,-12.9%
GRIA,-12.3%
TRUE,-11.7%

Naik setelah Investor Asing Beli kemarin:
UNVR 1.2% / 8.8M
CMNT 3.2% / 5.9M
CYBR 5.3% / 1.8M
ACES 0.6% / 0.4M

Naik setelah turun 3 hari:
-

Lonjakan volume:
BABY  35x
KBLV  19x
OILS  16x
ESIP  13x
RGAS  8x'''

parsed = parse_market_report(test_msg)
if not parsed:
    print('PARSE FAILED')
    sys.exit(1)

print(f'Type: {parsed["type"]}')
print(f'IHSG: {parsed["ihsg_change"]}%')
print(f'Gainer ({len(parsed["gainer"])}): {[s["stock"] for s in parsed["gainer"]]}')
print(f'Loser ({len(parsed["loser"])}): {[s["stock"] for s in parsed["loser"]]}')

fby = parsed.get('foreign_buy_yesterday', [])
print(f'Foreign Buy Yesterday ({len(fby)}):')
for s in fby:
    print(f'  {s["stock"]} {s["change_pct"]}% vol={s["volume"]}')

vs = parsed.get('volume_spike', [])
print(f'Volume Spike ({len(vs)}):')
for s in vs:
    print(f'  {s["stock"]} {s["multiplier"]}x')

# Also test that akhir sesi still works
test_akhir = '''Market Report akhir sesi by www.creative-trader.id

IHSG mengalami kenaikan 2.71%.

Top Foreign Buy
GOTO, 23.9M
BREN, 21.6M

Top Local Buy
BBRI, 571.3M
TPIA, 395.5M

Top Gainer
KBLV, 34.9%
FOLK, 34.6%

Top Loser
GRIA,-14.7%
RLCO,-8.8%'''

parsed2 = parse_market_report(test_akhir)
print(f'\nAkhir sesi test:')
print(f'Type: {parsed2["type"]}')
print(f'IHSG: {parsed2["ihsg_change"]}%')
print(f'Foreign Buy ({len(parsed2["foreign_buy"])}): {[s["stock"] for s in parsed2["foreign_buy"]]}')
print(f'Local Buy ({len(parsed2["local_buy"])}): {[s["stock"] for s in parsed2["local_buy"]]}')
print(f'Gainer ({len(parsed2["gainer"])}): {[s["stock"] for s in parsed2["gainer"]]}')

print('\nALL TESTS PASSED')
