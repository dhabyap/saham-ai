import json

for f, nama in [('brms_ajaib_20260708_20260803.json', 'BRMS'), ('brpt_ajaib_20260708_20260803.json', 'BRPT')]:
    d = json.load(open(f'data/raw/{f}'))
    res = d['result']
    ov = res['overview']
    print(f"\n{'='*50}\n{nama} OVERVIEW: value {ov['value']:,} lot {ov['lot']:,} foreign {ov['foreign_value']:,} avg {ov['avg']} | distribusi {res['distribution']}")

    def top(lst, n=5):
        lst = sorted(lst, key=lambda x: x.get('value', 0), reverse=True)
        out = []
        for x in lst[:n]:
            b = x['broker']
            out.append(f"  {b['code']} {b['name'][:28]:30} {x['value']/1e9:8.2f}B  lot {x['lot']:,}")
        return '\n'.join(out)

    print(f"\nTOP BUY:\n{top(res['summary_buy'])}")
    print(f"\nTOP SELL:\n{top(res['summary_sell'])}")

    fb = sum(x['value'] for x in res['summary_buy'] if x['broker']['category'] == 'FOREIGN_BROKER')
    lb = sum(x['value'] for x in res['summary_buy'] if x['broker']['category'] == 'LOCAL_BROKER')
    fs = sum(x['value'] for x in res['summary_sell'] if x['broker']['category'] == 'FOREIGN_BROKER')
    ls = sum(x['value'] for x in res['summary_sell'] if x['broker']['category'] == 'LOCAL_BROKER')
    print(f"\nFLOW: Foreign Buy {fb/1e9:.1f}B | Local Buy {lb/1e9:.1f}B | Foreign Sell {fs/1e9:.1f}B | Local Sell {ls/1e9:.1f}B")
    print(f"  Net Foreign: {(fb-fs)/1e9:+.2f}B  Net Local: {(lb-ls)/1e9:+.2f}B")
