"""Importer: Arthara RSC payload → DB
Support 3 RSC formats:
  F1: {brokers: [{code,side,total_net_value,flow:[{date,net_value,cumulative}]}]}
  F2: {brokerDataAggregated: {broker_summary: {buyers:[], sellers:[]}}}
  F3: {broker_summary: {buyers:[], sellers:[]}, crossing_analysis:{...}}

Usage:
  python3 import_arthara.py <rsc_file>
"""

import sys, json, os, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def parse_rsc_file(filepath):
    """Parse Arthara RSC payload, auto-detect format."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Strip user message prefix if present (e.g. "u can get this? and save in db 0:{...")
    lines = content.split('\n')
    data_line = None
    for line in lines:
        if line.startswith('1:'):
            data_line = line[2:]
            break

    if not data_line:
        # Try no prefix
        for line in lines:
            if line.startswith('{'):
                data_line = line
                break

    if not data_line:
        print(f"ERROR: RSC line '1:' not found")
        return None

    try:
        data = json.loads(data_line)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse: {e}")
        return None

    return data


def detect_format(data):
    """Detect RSC response format."""
    if 'brokers' in data and isinstance(data['brokers'], list):
        return 'daily_flow'  # F1 — daily net_value per broker
    if 'broker_summary' in data:
        return 'broker_summary'  # F3 — aggregated summary + crossing
    if 'brokerDataAggregated' in data:
        return 'broker_aggregated'  # F2 — aggregated summary
    return None


def import_daily_flow(conn, ticker, data):
    """F1: daily net flow per broker → broker_transactions table."""
    from app.database.broker_models import save_broker_transactions

    transactions = []
    for broker in data['brokers']:
        code = broker['code']
        for flow in broker.get('flow', []):
            date = flow['date']
            net = flow['net_value']
            if net == 0:
                continue

            if net >= 0:
                tx = {'broker_code': code, 'buy_volume': 0, 'sell_volume': 0,
                      'buy_value': abs(net), 'sell_value': 0}
            else:
                tx = {'broker_code': code, 'buy_volume': 0, 'sell_volume': 0,
                      'buy_value': 0, 'sell_value': abs(net)}

            transactions.append((date, tx))

    total = 0
    by_date = {}
    for trade_date, tx in transactions:
        by_date.setdefault(trade_date, []).append(tx)
    for date in sorted(by_date.keys()):
        total += save_broker_transactions(ticker, date, by_date[date])

    return total


def import_broker_summary(conn, ticker, data):
    """F2/F3: aggregated buyer/seller summary → broker_summary table."""
    f = data.get('broker_summary') or data.get('brokerDataAggregated', {}).get('broker_summary', {})
    if not f:
        return 0

    from_dt = data.get('from_date') or data.get('from')
    to_dt = data.get('to_date') or data.get('to')
    is_gross = data.get('is_gross', False)

    saved = 0

    def save_side(bs_side, side_name):
        nonlocal saved
        for b in bs_side:
            bc = b.get('broker_code')
            if not bc:
                continue
            lots = b.get('lots', 0)
            val = b.get('value', 0)
            avg = b.get('avg_price', 0)
            sql = """INSERT INTO broker_summary 
              (stock_code, period_from, period_to, is_gross, broker_code, side, lots, value, avg_price)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
              ON CONFLICT(stock_code, broker_code, side, period_from, period_to) DO UPDATE SET
              lots=excluded.lots, value=excluded.value, avg_price=excluded.avg_price"""
            conn.execute(sql, (ticker, from_dt, to_dt, int(is_gross), bc, side_name,
                               int(lots), float(val), float(avg)))
            saved += 1

    if 'buyers' in f:
        save_side(f['buyers'], 'buy')
    if 'sellers' in f:
        save_side(f['sellers'], 'sell')

    return saved


def print_summary(data, ftype):
    """Print analysis summary."""
    ticker = data.get('ticker', '?')
    period_from = data.get('from_date') or data.get('from', '?')
    period_to = data.get('to_date') or data.get('to', '?')
    is_gross = data.get('is_gross', False)

    print(f"\n{'='*60}")
    print(f"  FORMAT: {ftype}")
    print(f"  Ticker: {ticker}")
    print(f"  Period: {period_from} → {period_to}")
    if is_gross:
        print(f"  Type: GROSS (buy + sell)")
    else:
        print(f"  Type: NET")

    if ftype == 'daily_flow':
        brokers = data.get('brokers', [])
        avail = data.get('available_brokers', [])
        total_flow = sum(len(b.get('flow', [])) for b in brokers)
        print(f"  Brokers: {len(brokers)}")
        print(f"  Flow entries: {total_flow}")
        print("\n  Top Buyers:")
        for b in avail:
            if b.get('side') == 'buy':
                print(f"    {b['code']}: Rp{abs(b['total_net_value']):>12,.0f}")
        print("\n  Top Sellers:")
        for b in avail:
            if b.get('side') == 'sell':
                print(f"    {b['code']}: Rp{abs(b['total_net_value']):>12,.0f}")

    elif ftype in ('broker_summary', 'broker_aggregated'):
        bs = data.get('broker_summary') or data.get('brokerDataAggregated', {}).get('broker_summary', {})
        buyers = bs.get('buyers', [])
        sellers = bs.get('sellers', [])
        print(f"  Buyers: {len(buyers)} brokers")
        print(f"  Sellers: {len(sellers)} brokers")

        print("\n  Top 10 Buyers:")
        for b in sorted(buyers, key=lambda x: x.get('value', 0), reverse=True)[:10]:
            print(f"    {b['broker_code']}: lots={b['lots']:,}  Rp{b.get('value',0):,.0f}  avg=Rp{b.get('avg_price',0):,.0f}")

        print("\n  Top 10 Sellers:")
        for b in sorted(sellers, key=lambda x: x.get('value', 0), reverse=True)[:10]:
            print(f"    {b['broker_code']}: lots={b['lots']:,}  Rp{b.get('value',0):,.0f}  avg=Rp{b.get('avg_price',0):,.0f}")

        # net flow per broker
        print("\n  Net Flow (Top 10 Buy-side):")
        buy_map = {b['broker_code']: b.get('value', 0) for b in buyers}
        sell_map = {b['broker_code']: b.get('value', 0) for b in sellers}
        all_codes = set(list(buy_map.keys()) + list(sell_map.keys()))
        nets = []
        for code in all_codes:
            bv = buy_map.get(code, 0)
            sv = sell_map.get(code, 0)
            net = bv - sv
            nets.append((code, net, bv, sv))
        nets.sort(key=lambda x: x[1], reverse=True)
        for code, net, bv, sv in nets[:10]:
            label = f"+Rp{net:,.0f}" if net >= 0 else f"Rp{net:,.0f}"
            print(f"    {code}: {label}  (B: Rp{bv:,.0f} | S: Rp{sv:,.0f})")

        # crossing analysis
        ca = data.get('crossing_analysis', {})
        if ca:
            two_way = ca.get('two_way_brokers', [])
            if two_way:
                print("\n  Two-Way Brokers (top 5 by volume):")
                for b in sorted(two_way, key=lambda x: x['total_volume'], reverse=True)[:5]:
                    print(f"    {b['broker_code']}: B={b['buy_lots']:,} S={b['sell_lots']:,} "
                          f"Vol={b['total_volume']:,} 2W%={b['two_way_percentage']:.1f}%")

            pc = ca.get('potential_crossings', [])
            print(f"\n  Potential Crossings: {len(pc)} pairs")
            if pc:
                print(f"    Avg spread: Rp{ca['average_spread']:,.0f}")
                print(f"    Tightest:   Rp{ca['tightest_spread']:,.0f}")
                print(f"    Widest:     Rp{ca['widest_spread']:,.0f}")

    print(f"{'='*60}")


def format_nice(ticker, data, ftype):
    """Pretty markdown summary for user."""
    lines = []
    period = f"{data.get('from_date') or data.get('from', '?')} → {data.get('to_date') or data.get('to', '?')}"
    lines.append(f"**{ticker.upper()}** — {period}")
    lines.append("")

    if ftype == 'daily_flow':
        brokers = data['brokers']
        avail = data.get('available_brokers', [])
        total_flow = sum(len(b.get('flow', [])) for b in brokers)
        lines.append(f"• {len(brokers)} broker — {total_flow} flow entries")
        lines.append("")
        buy_list = [b for b in avail if b.get('side') == 'buy']
        sell_list = [b for b in avail if b.get('side') == 'sell']
        lines.append(f"Top Buyers:")
        for b in buy_list[:5]:
            lines.append(f"  • {b['code']}: +Rp{abs(b['total_net_value']):,.0f}")
        lines.append("")
        lines.append(f"Top Sellers:")
        for b in sell_list[:5]:
            lines.append(f"  • {b['code']}: -Rp{abs(b['total_net_value']):,.0f}")

    elif ftype in ('broker_summary', 'broker_aggregated'):
        bs = data.get('broker_summary') or data.get('brokerDataAggregated', {}).get('broker_summary', {})
        buyers = bs.get('buyers', [])
        sellers = bs.get('sellers', [])
        is_gross = data.get('is_gross', False)
        lines.append(f"• {len(buyers)} buyer / {len(sellers)} seller broker")
        lines.append("")

        # Net flow
        bmap = {b['broker_code']: b.get('value', 0) for b in buyers}
        smap = {b['broker_code']: b.get('value', 0) for b in sellers}
        codes = set(list(bmap.keys()) + list(smap.keys()))
        nets = []
        for c in codes:
            nets.append((c, bmap.get(c, 0) - smap.get(c, 0), bmap.get(c, 0), smap.get(c, 0)))
        nets.sort(key=lambda x: x[1], reverse=True)

        lines.append(f"Net flow (top 5 buyers):")
        for c, n, bv, sv in nets[:5]:
            label = f"+Rp{n:,.0f}" if n >= 0 else f"-Rp{abs(n):,.0f}"
            lines.append(f"  • {c}: {label}")
        lines.append("")
        lines.append(f"Net flow (top 5 sellers):")
        for c, n, bv, sv in reversed(nets[-5:]):
            label = f"-Rp{abs(n):,.0f}" if n < 0 else f"+Rp{n:,.0f}"
            lines.append(f"  • {c}: {label}")

        ca = data.get('crossing_analysis', {})
        if ca:
            tw = ca.get('two_way_brokers', [])
            if tw:
                top2w = max(tw, key=lambda x: x['total_volume'])
                lines.append("")
                lines.append(f"Top 2-way: {top2w['broker_code']} ({top2w['two_way_percentage']:.1f}% 2-way)")
                # Most lopsided
                most_lopsided = min(tw, key=lambda x: x['two_way_percentage'])
                lines.append(f"Most 1-way: {most_lopsided['broker_code']} ({most_lopsided['two_way_percentage']:.1f}% 2-way)")

            pc = ca.get('potential_crossings', [])
            lines.append(f"\nPotential crossings: {len(pc)} pairs")
            if pc:
                widest = max(pc, key=lambda x: x.get('spread', 0))
                lines.append(f"Widest: {widest['buyer_broker']}→{widest['seller_broker']} spread Rp{widest['spread']:,.0f}")

    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_arthara.py <rsc_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    data = parse_rsc_file(filepath)
    if not data:
        sys.exit(1)

    ftype = detect_format(data)
    if not ftype:
        print("ERROR: Unknown format. Keys:", list(data.keys()))
        sys.exit(1)

    print_summary(data, ftype)
    ticker = data.get('ticker', 'UNKNOWN')

    # Try project DB
    try:
        os.environ['DB_DRIVER'] = 'mysql'
        from app.database.database import get_db, DB_TYPE

        with get_db() as conn:
            if ftype == 'daily_flow':
                saved = import_daily_flow(conn, ticker, data)
                print(f"\n  ✓ {saved} entries to broker_transactions ({DB_TYPE})")
            elif ftype in ('broker_summary', 'broker_aggregated'):
                saved = import_broker_summary(conn, ticker, data)
                if saved:
                    print(f"\n  ✓ {saved} entries to broker_summary ({DB_TYPE})")
    except Exception as e:
        print(f"\n  ✗ DB save error: {e}")
        print("  (summary printed above)")

    # Print nice version for user
    nice = format_nice(ticker, data, ftype)
    print("\n\n" + nice)
