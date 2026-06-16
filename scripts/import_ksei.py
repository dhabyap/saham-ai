"""Parse KSEI shareholder PDF and import into analisa-saham DB."""
import pdfplumber
import re
import sys
import os
sys.path.insert(0, 'D:\\Latihan\\Saham\\analisa-saham')

def parse_pdf(path):
    """Extract rows from KSEI PDF format."""
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('DATE') or line.startswith('*') or line.startswith('*Penafian') or line.startswith('*Disclaimer'):
                    continue
                # Format: 27-Feb-2026CODE ISSUER_NAME ... PERCENTAGE
                # DATE is 13 chars: "27-Feb-2026"
                # SHARE_CODE starts right after date
                m = re.match(r'(\d{2}-[A-Z][a-z]{2}-\d{4})([A-Z]{3,5})\s', line)
                if not m:
                    continue
                date = m.group(1)
                code = m.group(2)
                rest = line[m.end():]
                
                # Find percentage at end (comma as decimal separator)
                pct_m = re.search(r'([\d\.]+),(\d{2})\s*$', rest)
                if not pct_m:
                    continue
                pct_str = pct_m.group(1) + '.' + pct_m.group(2)
                pct = float(pct_str)
                
                rest2 = rest[:pct_m.start()].strip()
                
                # Find total shares at end of rest2
                # Pattern: number with dots followed by 0 or space
                shares_m = re.search(r'([\d\.]+)\s+0\s*$', rest2)
                if not shares_m:
                    shares_m = re.search(r'0\s+([\d\.]+)\s*$', rest2)
                if not shares_m:
                    # Try: TOTAL_HOLDING_SHARES at end
                    share_parts = re.findall(r'([\d\.]+)', rest2)
                    if len(share_parts) >= 2:
                        total_shares_str = share_parts[-1].replace('.', '')
                        total_shares = int(total_shares_str) if total_shares_str.isdigit() else 0
                    else:
                        total_shares = 0
                else:
                    total_shares_str = shares_m.group(1).replace('.', '')
                    total_shares = int(total_shares_str) if total_shares_str.isdigit() else 0
                    rest2 = rest2[:shares_m.start()].strip()

                if total_shares == 0 and pct > 0:
                    total_shares = int(pct * 1000000)  # fallback

                # Extract investor name from remaining text
                # Remove LOCAL_FOREIGN code (single char D or F) and everything after
                rest2 = re.sub(r'\s+[DF]\s+.*$', '', rest2)
                investor_name = rest2.strip().rstrip(',')

                if investor_name and pct >= 1.0:
                    rows.append((code, investor_name, pct, total_shares, 'JUN2026'))
                    if len(rows) % 100 == 0:
                        print(f'  Parsed {len(rows)} rows...', file=sys.stderr)
    
    return rows

def import_rows(rows):
    """Import via API."""
    import requests
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    batch_size = 200
    total = len(rows)
    imported = 0
    
    for i in range(0, total, batch_size):
        batch = rows[i:i+batch_size]
        data = [{
            "stock_code": r[0],
            "shareholder_name": r[1],
            "share_percent": r[2],
            "share_count": r[3],
        } for r in batch]
        
        try:
            resp = requests.post(
                'http://localhost:8000/api/shareholders/import',
                json={"period": "JUN2026", "data": data},
                timeout=30
            )
            result = resp.json()
            if result.get('status') == 'ok':
                imported += result.get('imported', 0)
            else:
                print(f'  Batch {i//batch_size} FAILED: {result}', file=sys.stderr)
        except Exception as e:
            print(f'  Batch {i//batch_size} ERROR: {e}', file=sys.stderr)
        
        if (i // batch_size) % 5 == 0:
            print(f'  Progress: {i}/{total} - imported: {imported}', file=sys.stderr)
    
    return imported

if __name__ == '__main__':
    pdf_path = 'C:/Users/dhaby/AppData/Local/hermes/cache/documents/doc_4ae1301d0146_b9b638e5a8_8928aca255.pdf'
    print('Parsing PDF...', file=sys.stderr)
    rows = parse_pdf(pdf_path)
    print(f'Found {len(rows)} rows with >1% holdings', file=sys.stderr)
    
    # Print sample
    for r in rows[:5]:
        print(f'  {r[0]:5s} | {r[1]:40s} | {r[2]:6.2f}% | {r[3]:>12,}')
    
    print(file=sys.stderr)
    print('Importing...', file=sys.stderr)
    imp = import_rows(rows)
    print(f'Done. Imported: {imp} / {len(rows)}', file=sys.stderr)
