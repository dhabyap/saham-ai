import json

s = open('C:/Users/dhaby/AppData/Local/hermes/cache/documents/doc_4d1404337d0e_message.txt','r').read()
line2 = s.split(chr(10))[1]
if line2.startswith('1:'):
    line2 = line2[2:]
data = json.loads(line2)

print('=== AVAILABLE BROKERS (sorted by absolute value) ===')
for b in data['available_brokers'][:30]:
    side = 'BUY ' if b['side']=='buy' else 'SELL'
    val = abs(b['total_net_value'])
    print('  %s: %s Rp%s' % (b['code'], side, f'{val:,.0f}'))

print()
print('=== DETAILED BROKER FLOW (last 10 days) ===')
for b in data['brokers'][:5]:
    print()
    label = 'BUYER' if b['side']=='buy' else 'SELLER'
    print('Broker: %s (%s)' % (b['code'], label))
    print('  Total Net: Rp%s' % f'{abs(b["total_net_value"]):,.0f}')
    print('  Flow (last 10):')
    for f in b['flow'][-10:]:
        print('    %s: net=%+d cum=%+d' % (f['date'], f['net_value'], f['cumulative']))
