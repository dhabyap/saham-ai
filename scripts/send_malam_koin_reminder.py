#!/usr/bin/env python3
"""Send SCREENING MALAM KOIN reminder to Telegram (Indonesia)."""
import os, json, urllib.request

# Load .env (one level up)
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
    print('ERROR: token or chat_id not found')
    exit(1)

text = """🌙 <b>SCREENING MALAM KOIN (19:00)</b>\n\n1. Buka AlphaTracker (port 8003) — scan whale wallet baru\n2. Cek volume spike / breakout\n3. Update watchlist koin\n4. Catat potensi swing besok"""

data = json.dumps({'chat_id': chat_id, 'parse_mode': 'HTML', 'text': text}).encode('utf-8')
req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as r:
    resp = json.loads(r.read())
print('OK:', resp.get('ok'))
