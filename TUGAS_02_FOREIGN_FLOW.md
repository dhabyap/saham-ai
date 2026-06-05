# Tugas 2: Foreign & Institutional Flow Data

## Target

Buat sistem pengambilan, penyimpanan, dan analisis data **foreign flow** (foreign buy/sell/net) untuk saham IDX. Ini komponen scoring 35% di METODE_ANALISIS.md — paling besar bobotnya.

---

## Sumber Data

Karena public API untuk foreign flow IDX terbatas, gunakan 2 sumber:

1. **RTI Business** (scraping) — Sumber utama, via `https://rti.biz/id/` atau endpoint alternatif
2. **IDX Stock Summary** — Cadangan, via `https://www.idx.co.id/`

⚠️ **Catatan:** Jika scraping gagal/gak akurat, implementasi harus punya **fallback ke rule-based estimation** (Bagian D).

---

## Arsitektur

```
Scheduler (APScheduler) → foreign_flow_scraper → Database (foreign_flow table)
                                                       ↓
Analysis Service → ForeignFlowAnalyzer → Database (query)
```

---

## Bagian A: Model Database

### File Baru: `app/database/foreign_flow_models.py`

Ini definisi SQLite schema untuk data foreign flow.

### Tabel: `foreign_flow`

```sql
CREATE TABLE IF NOT EXISTS foreign_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,           -- format: YYYY-MM-DD
    foreign_buy REAL DEFAULT 0,         -- volume foreign buy (Rp)
    foreign_sell REAL DEFAULT 0,        -- volume foreign sell (Rp)
    foreign_net REAL DEFAULT 0,         -- foreign_buy - foreign_sell
    domestic_buy REAL DEFAULT 0,        -- volume domestic buy (Rp)
    domestic_sell REAL DEFAULT 0,       -- volume domestic sell (Rp)
    total_volume REAL DEFAULT 0,        -- total volume (Rp)
    foreign_buy_volume INTEGER DEFAULT 0,  -- jumlah lot foreign buy
    foreign_sell_volume INTEGER DEFAULT 0, -- jumlah lot foreign sell
    last_price REAL DEFAULT 0,          -- harga closing hari itu
    source TEXT DEFAULT 'rti',          -- 'rti', 'idx', 'estimated'
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(stock_code, trade_date)      -- 1 baris per saham per hari
);
```

### Tabel: `foreign_accumulation`

```sql
CREATE TABLE IF NOT EXISTS foreign_accumulation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    cumulative_net REAL DEFAULT 0,      -- net flow kumulatif 5 hari
    accumulation_days INTEGER DEFAULT 0,  -- berapa hari berturut-turut net buy
    distribution_days INTEGER DEFAULT 0,  -- berapa hari berturut-turut net sell
    avg_net_5d REAL DEFAULT 0,          -- rata-rata net 5 hari
    avg_net_20d REAL DEFAULT 0,         -- rata-rata net 20 hari
    status TEXT DEFAULT 'neutral',      -- 'accumulating', 'distributing', 'neutral'
    strength TEXT DEFAULT 'weak',       -- 'strong', 'moderate', 'weak'
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(stock_code, trade_date)
);
```

### Fungsi DB di file yang sama:

```python
def init_foreign_flow_db():
    """Buat tabel foreign_flow dan foreign_accumulation jika belum ada."""

def save_foreign_flow(data: list[dict]):
    """Insert/update baris foreign_flow. data adalah list of dict."""

def get_foreign_flow(stock_code: str, days: int = 30) -> list[dict]:
    """Ambil history foreign flow untuk satu saham, diurutkan DESC by date."""

def get_accumulation_status(stock_code: str) -> Optional[dict]:
    """Ambil status akumulasi terkini untuk satu saham."""

def get_all_accumulation_status() -> list[dict]:
    """Ambil status akumulasi semua saham, urut berdasarkan accumulation_days DESC."""

def update_accumulation(stock_code: str, trade_date: str):
    """Hitung ulang akumulasi untuk satu saham pada tanggal tertentu.
    
    Logic:
    1. Ambil 20 hari terakhir foreign_flow untuk stock_code
    2. cumulative_net = SUM(foreign_net) untuk 5 hari terakhir
    3. accumulation_days = hitung berapa hari berturut-turut foreign_net > 0 (mundur dari hari terakhir)
    4. distribution_days = hitung berapa hari berturut-turut foreign_net < 0 (mundur dari hari terakhir)
    5. avg_net_5d = AVG(foreign_net) 5 hari
    6. avg_net_20d = AVG(foreign_net) 20 hari
    7. status:
       - 'accumulating' jika accumulation_days >= 3
       - 'distributing' jika distribution_days >= 3
       - 'neutral' sisanya
    8. strength:
       - 'strong' jika avg_net_5d > 0 AND avg_net_20d > 0
       - 'moderate' jika salah satu positif
       - 'weak' jika keduanya negatif
    9. Insert/update tabel foreign_accumulation
    """
```

---

## Bagian B: Scraper / Data Fetcher

### File Baru: `app/services/foreign_flow.py`

### Fungsi 1: `fetch_foreign_flow_rti(stock_code: str, date: str = None) -> Optional[dict]`

**Logic:**
- Coba scraping RTI Business untuk data foreign flow
- URL pattern: `https://rti.biz.id/emiten/{stock_code_lower}` atau `https://www.rti.co.id/stock/{stock_code}`
- Parse HTML/extract JSON untuk foreign buy/sell
- Return dict dengan format:
```python
{
    "stock_code": "BBCA",
    "trade_date": "2026-06-05",
    "foreign_buy": 250000000000,    # Rp 250 M
    "foreign_sell": 180000000000,   # Rp 180 M
    "foreign_net": 70000000000,     # Rp 70 M (net buy)
    "domestic_buy": 500000000000,
    "domestic_sell": 570000000000,
    "total_volume": 750000000000,
    "last_price": 10250,
    "source": "rti"
}
```
- Jika scraping gagal (HTTP error, HTML changed), return None
- **WAJIB** pakai `try/except` — jangan sampai crash

### Fungsi 2: `fetch_foreign_flow_idx(stock_code: str, date: str = None) -> Optional[dict]`

**Logic:**
- Fallback scraper dari IDX website
- URL: `https://www.idx.co.id/Portals/0/StaticData/Summary/{code}_Summary.xlsx`
- Parse file Excel
- Lebih lambat, return format sama seperti fetch_foreign_flow_rti()

### Fungsi 3: `fetch_and_save_foreign_flow(stock_code: str) -> bool`

**Logic:**
1. Panggil `fetch_foreign_flow_rti(stock_code)` — primary
2. Jika gagal, panggil `fetch_foreign_flow_idx(stock_code)` — fallback
3. Jika dapat data, panggil `save_foreign_flow([data])`
4. Panggil `update_accumulation(stock_code, trade_date)`
5. Return True jika sukses, False jika gagal total

### Fungsi 4: `sync_all_foreign_flow(stock_codes: list[str] = None) -> dict`

**Logic:**
- Loop semua stock_codes (default: semua dari STOCK_LIST)
- Panggil `fetch_and_save_foreign_flow(code)` untuk masing-masing
- Return summary: `{"success": 20, "failed": 5, "total": 25, "errors": ["BBCA: timeout", ...]}`

---

## Bagian C: Scheduler

### Modifikasi: `app/scheduler/tasks.py`

Tambah task baru:

```python
def sync_foreign_flow_task():
    """Di-run setiap hari jam 17:30 WIB (setelah market close IDX jam 16:00).
    
    Panggil sync_all_foreign_flow() untuk update semua data.
    """
```

### Modifikasi: `app/scheduler/scheduler.py`

Register jadwal sync foreign flow. Copy pattern dari task yang sudah ada.

---

## Bagian D: Rule-Based Estimation (Fallback)

Jika scraping foreign flow gagal total (website berubah, blokir, dll), implementasi harus punya fallback.

### Di `app/services/foreign_flow.py`:

### Fungsi 5: `estimate_foreign_flow_from_price_action(df: pd.DataFrame) -> dict`

**Logic:**
Estimasi foreign flow berdasarkan price action (rule of thumb):
- Volume spike + harga naik + range besar → kemungkinan foreign buy
- Volume spike + harga turun + range besar → kemungkinan foreign sell
- Gunakan regression sederhana untuk estimasi

```python
{
    "stock_code": "BBCA",
    "trade_date": today,
    "foreign_net": estimated_value,   # hasil estimasi
    "foreign_buy": estimated_buy,
    "foreign_sell": estimated_sell,
    "source": "estimated",
    "confidence": 0.65,               # 0.0 - 1.0 (seberapa yakin)
}
```

**Catatan:** Ini LAST RESORT. Data real selalu lebih baik.

---

## Bagian E: Endpoint API Baru

### Modifikasi: `app/api/routes.py`

### 1. `GET /api/foreign-flow/{code}`
Ambil history foreign flow untuk satu saham.
- Query param: `days` (default 30)
- Panggil `get_foreign_flow(code, days)`

**Response:**
```json
{
    "status": "ok",
    "data": {
        "stock_code": "BBCA",
        "history": [
            {"trade_date": "2026-06-05", "foreign_net": 70000000000, "status": "accumulating", ...},
            ...
        ],
        "accumulation_status": {
            "accumulation_days": 5,
            "status": "accumulating",
            "strength": "strong"
        }
    }
}
```

### 2. `GET /api/foreign-flow/summary`
Ringkasan foreign flow semua saham (top accumulating, top distributing).

**Response:**
```json
{
    "status": "ok",
    "data": {
        "top_accumulating": [{"code": "BBCA", "net_5d": ..., "days": 5}, ...],
        "top_distributing": [...],
        "total_tracked": 25,
        "last_sync": "2026-06-05T17:30:00"
    }
}
```

---

## Bagian F: Konfigurasi

### Modifikasi: `app/config.py`

Tambah:
```python
FOREIGN_FLOW_ENABLED = os.getenv("FOREIGN_FLOW_ENABLED", "true").lower() == "true"
FOREIGN_FLOW_SCHEDULE = os.getenv("FOREIGN_FLOW_SCHEDULE", "17:30")
FOREIGN_FLOW_DAYS_HISTORY = int(os.getenv("FOREIGN_FLOW_DAYS_HISTORY", "90"))
```

### Modifikasi: `.env.example`

Tambah:
```env
FOREIGN_FLOW_ENABLED=true
FOREIGN_FLOW_SCHEDULE=17:30
```

---

## Bagian G: Testing

### File Baru: `tests/test_foreign_flow.py`

1. Test `save_foreign_flow()` — insert data, query balik, assert match
2. Test `update_accumulation()` — insert 5 hari net buy, assert status = "accumulating"
3. Test `get_accumulation_status()` — query yang baru diinsert, assert valid
4. Test `estimate_foreign_flow_from_price_action()` — pake DataFrame mock, assert return valid

---

## Kriteria Selesai

- [ ] Tabel `foreign_flow` dan `foreign_accumulation` terbikin otomatis saat app start
- [ ] Scraper bisa ambil data foreign flow dari RTI (atau fallback)
- [ ] Kalau scraping gagal, fallback estimation berjalan
- [ ] Scheduler jalan otomatis tiap hari jam 17:30
- [ ] Endpoint `/api/foreign-flow/{code}` return data valid
- [ ] Endpoint `/api/foreign-flow/summary` return ringkasan
- [ ] Test file jalan tanpa error
- [ ] `python run.py` gak error

---
