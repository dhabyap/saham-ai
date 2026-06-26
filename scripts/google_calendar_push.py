#!/usr/bin/env python3
"""
Push jadwal harian ke Google Calendar.
Run after google_calendar_setup.py (token.pickle must exist).
"""
import os, pickle, json
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone

CREDENTIALS = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
TOKEN = os.path.join(os.path.dirname(__file__), '..', 'token.pickle')
TZ = 'Asia/Jakarta'
WIB = timezone(timedelta(hours=7))

WEEKDAYS = 'MO,TU,WE,TH,FR'

EVENTS = [
    {
        'summary': '🌅 Screening Koin Pagi + Data Broker',
        'description': '1. Buka AlphaTracker — scan whale, volume spike, sinyal baru\n2. Import RSC/Arthara (kalau ada file baru)\n3. Cek crossing summary semalam\n4. Cek net flow broker terbaru',
        'start': '05:30',
        'end': '06:30',
        'recurrence': 'FREQ=DAILY',
    },
    {
        'summary': '📊 Overview + AI Rekom Sesi 1',
        'description': '1. Overview Analisa-saham (IHSG, foreign flow, top movers)\n2. AI Rekomendasi broker data\n3. Cek dashboard Hermes — semua bot jalan?',
        'start': '08:00',
        'end': '08:30',
        'recurrence': f'FREQ=WEEKLY;BYDAY={WEEKDAYS}',
    },
    {
        'summary': '👀 Pantau Sesi 1 IDX',
        'description': '1. Net flow broker update\n2. Crossing movement\n3. Catat yang perlu dicek ulang nanti',
        'start': '09:00',
        'end': '09:45',
        'recurrence': f'FREQ=WEEKLY;BYDAY={WEEKDAYS}',
    },
    {
        'summary': '🍜 Istirahat + Cek Sesi 1',
        'description': '1. Cek net flow sesi 1 (closing?)\n2. AlphaTracker scan koin sebentar\n3. Import data broker kalau ada',
        'start': '12:00',
        'end': '12:45',
        'recurrence': f'FREQ=WEEKLY;BYDAY={WEEKDAYS}',
    },
    {
        'summary': '📈 Evaluasi Sesi 2 + AI Insight',
        'description': '1. Rangkuman net flow full hari\n2. Crossing terbesar hari ini\n3. AI Insight harian (Analisa-saham)',
        'start': '18:00',
        'end': '19:00',
        'recurrence': f'FREQ=WEEKLY;BYDAY={WEEKDAYS}',
    },
    {
        'summary': '🌙 Screening Malam Koin',
        'description': '1. AlphaTracker scan ulang market crypto\n2. Wallet whale baru\n3. Update watchlist',
        'start': '19:00',
        'end': '20:00',
        'recurrence': 'FREQ=DAILY',
    },
    {
        'summary': '📋 Persiapan Besok',
        'description': '1. Import data broker yang belum masuk\n2. Cek jadwal rilis data baru\n3. Backup ringan\n4. Pastikan AlphaTracker + semua cron aktif',
        'start': '20:30',
        'end': '21:00',
        'recurrence': 'FREQ=DAILY',
    },
]

def get_calendar_id(service):
    cals = service.calendarList().list().execute()
    for cal in cals.get('items', []):
        if cal.get('primary'):
            return cal['id']
    return 'primary'

def make_event(ev):
    today = datetime.now(WIB).strftime('%Y%m%d')
    start_dt = f"{today}T{ev['start']}:00"
    end_dt = f"{today}T{ev['end']}:00"
    rrule = f"DTSTART;TZID={TZ}:{today}T{ev['start']}:00\r\nRRULE:{ev['recurrence']}"
    return {
        'summary': ev['summary'],
        'description': ev['description'],
        'start': {
            'dateTime': start_dt,
            'timeZone': TZ,
        },
        'end': {
            'dateTime': end_dt,
            'timeZone': TZ,
        },
        'recurrence': [f"RRULE:{ev['recurrence']}"],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 5},
            ],
        },
    }

def main():
    creds = None
    if not os.path.exists(TOKEN):
        print("❌ token.pickle not found. Run google_calendar_setup.py first.")
        return
    with open(TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, 'wb') as f:
            pickle.dump(creds, f)
    service = build('calendar', 'v3', credentials=creds)
    cal_id = get_calendar_id(service)
    print(f"📅 Using calendar: {cal_id}")
    for ev in EVENTS:
        body = make_event(ev)
        created = service.events().insert(calendarId=cal_id, body=body).execute()
        print(f"✅ {ev['summary']} → {created.get('htmlLink', 'ok')}")
    print("\n🎉 All events created! Check Google Calendar.")

if __name__ == '__main__':
    main()
