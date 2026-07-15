#!/usr/bin/env python3
"""Send Sesi 1 IDX reminder to Telegram."""
import os, json, urllib.request

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
token = None
chat_id = None

with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            token = line.split('=', 1)[1].strip().strip("'\"")
        elif line.startswith('TELEGRAM_CHAT_ID='):
            chat_id = line.split('=', 1)[1].strip().strip("'\"")

if not token or not chat_id:
    print("ERROR: token or chat_id not found")
    exit(1)

text = """<b>⏰ SESI 1 IDX — Pantau (09:00-09:45)</b>

<b>1. Net Flow Broker</b>
• Buka tab <b>Net Flow</b>
• Cek net buy/sell hari ini

<b>2. Crossing Movement</b>
• Crossing terbaru — ada yang mencurigakan?

<b>3. AI Rekomendasi</b>
• Periksa tab AI Rekomendasi
• Ada perubahan signal?

Catat yang perlu dicek ulang nanti di sesi 2. 📝"""

data = json.dumps({'chat_id': chat_id, 'parse_mode': 'HTML', 'text': text}).encode('utf-8')
req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=data, headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
resp = json.loads(r.read())
print(f"OK: {resp.get('ok')}")
