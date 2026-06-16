"""
Script: Fetch & Import Shareholder >1% Data from IDX
=====================================================
Downloads PDF from IDX (monthly), parses tables, inserts into MySQL.
Run manually or via cron for monthly updates.

Usage:
  python scripts/fetch_shareholders.py          # Try download + import
  python scripts/fetch_shareholders.py --pdf path/to/file.pdf  # Import existing PDF
  python scripts/fetch_shareholders.py --list   # List available PDFs from IDX
"""

import os, sys, re, tempfile, argparse, logging, traceback
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
import pdfplumber

from app.config import Config
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ─── DB ──────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'analisa_saham'),
}

TABLE = 'shareholders'
DATA_PERIOD = ''  # set during download/parse

# ─── PDF DOWNLOAD ────────────────────────────────────────────────────

IDX_SEARCH = 'https://www.idx.id/id/search?q=Pemegang+Saham+di+atas+1%25'

def list_available_pdfs() -> list[dict]:
    """List available shareholder PDFs from IDX search."""
    import cloudscraper
    scraper = cloudscraper.create_scraper()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = scraper.get(IDX_SEARCH, headers=headers, timeout=30)
        if resp.status_code != 200:
            log.warning(f'IDX search returned {resp.status_code}')
            return []
    except Exception as e:
        log.error(f'Failed to reach IDX: {e}')
        return []

    # Extract PDF links
    pdfs = re.findall(r'href=[\"\'](https?://[^\"\']+\.pdf)[\"\']', resp.text)
    results = []
    seen = set()
    for url in pdfs:
        fname = url.split('/')[-1]
        if 'pemegang' in url.lower() or 'saham' in url.lower() or '1%' in url:
            # Extract date from filename
            m = re.match(r'(\d{4})(\d{2})(\d{2})', fname)
            date_str = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else 'unknown'
            if url not in seen:
                seen.add(url)
                results.append({'url': url, 'filename': fname, 'date': date_str})
    return sorted(results, key=lambda x: x['date'], reverse=True)


def download_pdf(url: str, output_path: str) -> bool:
    """Download a PDF, trying multiple methods to bypass Cloudflare."""
    import cloudscraper
    methods = []

    # Method 1: cloudscraper
    methods.append(('cloudscraper', lambda: cloudscraper.create_scraper().get(url, timeout=30)))

    # Method 2: requests with browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'application/pdf,*/*',
        'Accept-Language': 'id,en;q=0.9',
        'Referer': 'https://www.idx.id/',
    }

    def _requests_get():
        s = requests.Session()
        # First visit idx.id to get cookies
        s.get('https://www.idx.id/', headers=headers, timeout=15)
        return s.get(url, headers=headers, timeout=30)

    methods.append(('requests+session', _requests_get))

    for name, fn in methods:
        try:
            resp = fn()
            if resp.status_code == 200 and len(resp.content) > 10000 and b'%PDF' in resp.content[:100]:
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                log.info(f'Downloaded via {name}: {len(resp.content)} bytes -> {output_path}')
                return True
            elif resp.status_code == 200:
                log.debug(f'{name}: {len(resp.content)} bytes (may not be PDF)')
            else:
                log.debug(f'{name}: HTTP {resp.status_code}')
        except Exception as e:
            log.debug(f'{name} failed: {e}')

    return False


# ─── PDF PARSING ────────────────────────────────────────────────────

def parse_pdf(pdf_path: str) -> list[dict]:
    """Parse shareholder PDF and extract rows."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            log.info(f'Parsing page {page_num + 1}/{len(pdf.pages)}')

            # Try extracting tables
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        parsed = _parse_row(row)
                        if parsed:
                            rows.append(parsed)
            else:
                # Fallback: extract text and parse line by line
                text = page.extract_text()
                if text:
                    for line in text.split('\n'):
                        parsed = _parse_text_line(line)
                        if parsed:
                            rows.append(parsed)
    return rows


def _parse_row(row: list) -> Optional[dict]:
    """Parse a table row from the PDF."""
    if not row or len(row) < 3:
        return None

    # Clean cells
    cells = [str(c).strip() if c else '' for c in row]

    # Skip header/empty rows
    first = cells[0].upper()
    if any(kw in first for kw in ['EMITEN', 'KODE', 'NAMA', 'PEMEGANG', 'NO', 'TOTAL', 'SUBTOTAL']):
        return None
    if all(not c for c in cells):
        return None

    # Try to identify structure
    # Expected: [stock_code, shareholder_name, share_count, share_percent] or similar
    # Common IDX PDF columns: NO | KODE | NAMA PEMEGANG SAHAM | JUMLAH SAHAM | %

    stock_code = None
    shareholder_name = None
    share_count = 0
    share_percent = 0.0

    for cell in cells:
        cell = cell.replace(',', '').replace(' ', '')
        # Check if it looks like a stock code (4-5 uppercase letters)
        if re.match(r'^[A-Z]{3,5}$', cell) and not stock_code:
            stock_code = cell
            continue
        # Check if it looks like a percentage
        pct_match = re.search(r'(\d+[.,]?\d*)%', cell)
        if pct_match and not share_percent:
            share_percent = float(pct_match.group(1).replace(',', '.'))
            continue
        # Check if it looks like a number (share count)
        num_match = re.match(r'^(\d{4,})$', cell.replace('.', ''))
        if num_match and not share_count:
            share_count = int(num_match.group(1))
            continue

    # If we couldn't parse, try a simpler approach: first real-looking word = code, rest = name
    if not stock_code:
        for cell in cells:
            cell_clean = cell.strip().upper()
            if re.match(r'^[A-Z]{3,5}$', cell_clean) and cell_clean not in ['JUMLAH', 'NAMA', 'KODE', 'EMITEN', 'TOTAL', 'SAHAM', 'NO']:
                stock_code = cell_clean
                break

    if not stock_code or not any(c.strip() for c in cells if c.strip()):
        return None

    # Find shareholder name (everything between code and numbers)
    return {
        'stock_code': stock_code,
        'shareholder_name': '|'.join(c.strip() for c in cells if c.strip() and c.strip().upper() != stock_code),
        'share_count': share_count,
        'share_percent': share_percent,
    }


def _parse_text_line(line: str) -> Optional[dict]:
    """Parse a text line from PDF fallback."""
    line = line.strip()
    if not line or len(line) < 10:
        return None

    # Look for stock code pattern
    m = re.match(r'^([A-Z]{3,5})\s+(.+?)\s+(\d[\d,.]*)\s+(\d[\d,.]*)%?', line)
    if m:
        return {
            'stock_code': m.group(1),
            'shareholder_name': m.group(2).strip(),
            'share_count': int(m.group(3).replace(',', '')),
            'share_percent': float(m.group(4).replace(',', '.')),
        }

    m = re.match(r'^([A-Z]{3,5})\s+(.+?)\s+(\d+[.,]?\d*)%?\s*$', line)
    if m:
        pct = float(m.group(3).replace(',', '.'))
        if pct > 0 and pct <= 100:
            return {
                'stock_code': m.group(1),
                'shareholder_name': m.group(2).strip(),
                'share_count': 0,
                'share_percent': pct,
            }

    return None


# ─── DB INSERT ──────────────────────────────────────────────────────

def get_mysql_conn():
    import mysql.connector
    return mysql.connector.connect(**DB_CONFIG)


def ensure_table():
    conn = get_mysql_conn()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(20) NOT NULL,
            shareholder_name VARCHAR(255) NOT NULL,
            share_count BIGINT DEFAULT 0,
            share_percent DECIMAL(10,4) DEFAULT 0,
            category VARCHAR(50) DEFAULT NULL,
            data_period VARCHAR(10) NOT NULL,
            source VARCHAR(50) DEFAULT 'idx',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_holder (stock_code, shareholder_name, data_period)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cur.close()
    conn.close()
    log.info(f'Table {TABLE} ready')


def import_data(rows: list[dict], period: str):
    """Batch insert parsed rows into MySQL."""
    if not rows:
        log.warning('No data to import')
        return

    conn = get_mysql_conn()
    cur = conn.cursor()

    # Dedup by (stock_code, shareholder_name)
    seen = set()
    unique = []
    for r in rows:
        key = (r['stock_code'], r['shareholder_name'][:100])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    log.info(f'Importing {len(unique)} unique rows (from {len(rows)} total) for period {period}')

    sql = f"""INSERT INTO {TABLE}
        (stock_code, shareholder_name, share_count, share_percent, data_period, source)
        VALUES (%s, %s, %s, %s, %s, 'idx')
        ON DUPLICATE KEY UPDATE
        share_count = VALUES(share_count),
        share_percent = VALUES(share_percent),
        updated_at = CURRENT_TIMESTAMP"""

    batch = []
    for r in unique:
        batch.append((
            r['stock_code'],
            r['shareholder_name'][:255],
            r['share_count'],
            r['share_percent'],
            period,
        ))

        if len(batch) >= 500:
            cur.executemany(sql, batch)
            conn.commit()
            batch = []

    if batch:
        cur.executemany(sql, batch)
        conn.commit()

    cur.close()
    conn.close()
    log.info(f'Imported {len(unique)} rows into {TABLE}')
    return unique


# ─── SEED DATA FROM ARTICLES ────────────────────────────────────────
def get_seed_data() -> list[dict]:
    """Seed data from known public sources (Bisnis.com articles, etc)."""
    period = '2026-02'
    seeds = [
        # Lo Kheng Hong
        ('DILD', 'LO KHENG HONG', 696030000, 6.71),
        ('BMTR', 'LO KHENG HONG', 1060000000, 6.44),
        ('GJTL', 'LO KHENG HONG', 209890000, 6.02),
        ('ABMM', 'LO KHENG HONG', 154830000, 5.62),
        ('RALS', 'LO KHENG HONG', 153250000, 2.16),
        ('SRIL', 'LO KHENG HONG', 209339500, 1.02),
        # Anthoni Salim
        ('DCII', 'ANTHONI SALIM', 0, 11.12),
        ('DNET', 'ANTHONI SALIM', 0, 25.30),
        ('EMTK', 'ANTHONI SALIM', 0, 8.97),
        ('BBCA', 'ANTHONI SALIM', 0, 1.15),
        # Prajogo Pangestu
        ('BRPT', 'PRAJOGO PANGESTU', 0, 71.37),
        ('CUAN', 'PRAJOGO PANGESTU', 0, 84.10),
        ('TPIA', 'PRAJOGO PANGESTU', 0, 5.03),
        # Hapsoro
        ('ARKO', 'HAPSORO', 0, 2.04),
        ('MINA', 'HAPSORO', 0, 19.68),
        ('RAJA', 'HAPSORO', 0, 27.52),
        ('SINI', 'HAPSORO', 0, 9.00),
        ('UANG', 'HAPSORO', 0, 19.35),
    ]
    return [
        {'stock_code': s[0], 'shareholder_name': s[1], 'share_count': s[2], 'share_percent': s[3]}
        for s in seeds
    ]


# ─── MAIN ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Fetch & import IDX shareholder >1% data')
    parser.add_argument('--pdf', help='Path to existing PDF file (skip download)')
    parser.add_argument('--list', action='store_true', help='List available PDFs from IDX')
    parser.add_argument('--seed', action='store_true', help='Import seed data from known sources')
    parser.add_argument('--period', help='Data period (YYYY-MM). Auto-detected from PDF name if omitted')
    args = parser.parse_args()

    ensure_table()

    if args.list:
        pdfs = list_available_pdfs()
        if not pdfs:
            print('No PDFs found or IDX search unavailable.')
            print('Try: manually download from https://www.idx.id > search "Pemegang Saham di atas 1%"')
            return
        print(f'\n{"DATE":<15} {"FILENAME":<70} URL')
        print('-' * 150)
        for p in pdfs:
            print(f'{p["date"]:<15} {p["filename"]:<70} {p["url"]}')
        return

    if args.seed:
        log.info('Importing seed data from known sources...')
        rows = get_seed_data()
        import_data(rows, '2026-02')
        log.info('Seed data imported.')
        return

    rows = []
    global DATA_PERIOD

    if args.pdf:
        log.info(f'Parsing PDF: {args.pdf}')
        if args.period:
            DATA_PERIOD = args.period
        else:
            m = re.search(r'(\d{4})(\d{2})(\d{2})', os.path.basename(args.pdf))
            if m:
                DATA_PERIOD = f'{m.group(1)}-{m.group(2)}'
            else:
                DATA_PERIOD = datetime.now().strftime('%Y-%m')
        rows = parse_pdf(args.pdf)
    else:
        log.info('Attempting to download latest PDF from IDX...')
        pdfs = list_available_pdfs()
        if not pdfs:
            log.warning('Could not fetch PDF list from IDX.')
            log.info('Fallback options:')
            log.info('  1. python scripts/fetch_shareholders.py --seed   (seed data from articles)')
            log.info('  2. Manually download PDF from https://www.idx.id, then run:')
            log.info('     python scripts/fetch_shareholders.py --pdf path/to/file.pdf')
            return

        latest = pdfs[0]
        log.info(f'Latest PDF: {latest["filename"]} ({latest["date"]})')
        DATA_PERIOD = latest['date'][:7]

        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_path = tmp.name
        tmp.close()

        if download_pdf(latest['url'], tmp_path):
            rows = parse_pdf(tmp_path)
            os.unlink(tmp_path)
        else:
            log.warning('Could not download PDF. IDX behind Cloudflare.')
            os.unlink(tmp_path)
            log.info('Try: manually download PDF from IDX website, then:')
            log.info(f'  python scripts/fetch_shareholders.py --pdf /path/file.pdf --period {DATA_PERIOD}')
            return

    if rows:
        log.info(f'Parsed {len(rows)} rows from PDF')
        # Filter valid rows
        valid = [r for r in rows if r and r['stock_code'] and len(r['stock_code']) >= 2]
        if valid:
            import_data(valid, DATA_PERIOD)
            # Print summary
            codes = set(r['stock_code'] for r in valid)
            log.info(f'Done! {len(valid)} shareholders across {len(codes)} stocks')
        else:
            log.warning('No valid rows parsed. PDF structure may differ from expected.')
            log.info('Manual inspection recommended.')
    else:
        log.warning('No data parsed from PDF.')


if __name__ == '__main__':
    main()
