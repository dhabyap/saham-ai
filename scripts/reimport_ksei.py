"""Re-import KSEI data using proper table extraction."""
import sys, os
sys.path.insert(0, 'D:\\Latihan\\Saham\\analisa-saham')
import pdfplumber
from app.services.shareholder_service import bulk_import
from app.database.database import get_db

pdf_path = 'C:/Users/dhaby/AppData/Local/hermes/cache/documents/doc_4ae1301d0146_b9b638e5a8_8928aca255.pdf'

rows = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        if not tables: 
            continue
        for table in tables:
            for row in table[1:]:  # Skip header
                if not row or len(row) < 12:
                    continue
                code = row[1]
                investor = row[3]
                pct_str = row[11]
                shares_str = row[10]
                if not code or not investor or not pct_str:
                    continue
                # Clean percentage (comma → dot)
                pct = float(pct_str.replace(',', '.').replace(' ', ''))
                # Clean shares
                shares = int(shares_str.replace('.', '').replace(' ', '')) if shares_str else 0
                investor = investor.strip()
                if pct >= 1.0:
                    rows.append({
                        'stock_code': code.strip(),
                        'shareholder_name': investor,
                        'share_percent': pct,
                        'share_count': shares,
                    })

print(f'Parsed: {len(rows)} rows')

# Sample
from collections import Counter
stocks = Counter(r['stock_code'] for r in rows)
print(f'Unique stocks: {len(stocks)}')
unique_holders = set()
for r in rows:
    unique_holders.add(r['shareholder_name'])
print(f'Unique holders: {len(unique_holders)}')
print()
for r in rows[:5]:
    pct_str2 = f'{r["share_percent"]:6.2f}%'
    cnt_str = f'{r["share_count"]:>12,}'
    print(f'  {r["stock_code"]:5s} | {r["shareholder_name"]:40s} | {pct_str2} | {cnt_str}')

# Clear old data
with get_db() as conn:
    conn.execute("DELETE FROM shareholders WHERE data_period = 'JUN2026'")
    conn.execute("DELETE FROM shareholders WHERE data_period = 'FEB2026'")
    conn.commit()
print('\nOld data cleared')

# Import
batch_size = 200
total = len(rows)
imported = 0
for i in range(0, total, batch_size):
    batch = rows[i:i+batch_size]
    result = bulk_import(batch, 'JUN2026')
    imported += result.get('imported', 0)
    if (i // batch_size) % 10 == 0:
        print(f'  Progress: {i}/{total} - imported: {imported}')

print(f'\nDone! Imported: {imported}')
