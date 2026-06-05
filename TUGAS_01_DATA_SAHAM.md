# Tugas 1: Data IHSG + Relative Strength

## Target

Buat sistem pengambilan data **IHSG (^JKSE)** dan hitung **Relative Strength** tiap saham terhadap IHSG. Ini komponen scoring 15% di METODE_ANALISIS.md.

---

## Bagian A: Service IHSG

### File Baru: `app/services/ihsg_service.py`

Buat class `IHSGService` yang handle semua operasi terkait data indeks.

```python
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np
import requests
```

### Fungsi 1: `fetch_ihsg_data(period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]`

**Logic:**
- Panggil Yahoo Finance endpoint: `https://query1.finance.yahoo.com/v8/finance/chart/^JKSE?range={period}&interval={interval}`
- Parse response → DataFrame dengan kolom: `Date` (index), `Open`, `High`, `Low`, `Close`, `Volume`
- Drop NaN rows
- Return None jika gagal (rate limit, timeout, empty data)
- Retry logic (3x, exponential backoff) — copy pattern dari `stock_service.fetch_stock_data()`
- **Rate limit handling**: 429 → sleep → retry

**Contoh return:**
```
Date                          Open    High     Low   Close    Volume
2025-06-05 00:00:00+00:00  6942.0  6981.0  6930.0  6975.0  1.23e10
...
```

### Fungsi 2: `get_ihsg_summary() -> dict`

**Logic:**
- Ambil data IHSG 1 bulan terakhir
- Hitung:
  - `current_price`: Close terakhir
  - `change_pct`: perubahan % 1 hari
  - `weekly_change`: perubahan % 1 minggu
  - `monthly_change`: perubahan % 1 bulan
  - `ytd_change`: perubahan % year-to-date (ambil data 1y)
  - `trend`: "Bullish" jika MA20 > MA50, "Bearish" jika sebaliknya
  - `support`: lowest low 20 hari terakhir
  - `resistance`: highest high 20 hari terakhir
  - `volume_trend`: "Increasing" jika volume 5 hari > volume 20 hari rata-rata

**Contoh return:**
```python
{
    "current_price": 6975.0,
    "change_pct": 0.45,
    "weekly_change": -0.23,
    "monthly_change": 2.15,
    "ytd_change": -1.82,
    "trend": "Bullish",
    "support": 6890.0,
    "resistance": 7010.0,
    "volume_trend": "Increasing",
    "last_updated": "2026-06-05T09:00:00"
}
```

### Fungsi 3: `get_historical_ihsg(days: int = 365) -> list[dict]`

**Logic:**
- Ambil data historis IHSG sebanyak `days` hari
- Return list of dict: `[{"date": "...", "close": 6975.0, "ma20": ..., "ma50": ...}, ...]`
- Include MA20, MA50 dalam tiap entry

---

## Bagian B: Relative Strength

### File Baru: `app/services/relative_strength.py`

```python
from typing import Optional
import pandas as pd
import numpy as np
```

### Fungsi 1: `calculate_relative_strength(stock_code: str, period: int = 63) -> Optional[dict]`

**Logic:**
- Ambil data saham 6 bulan (`fetch_stock_data(code, period="6mo")`)
- Ambil data IHSG 6 bulan (`fetch_ihsg_data(period="6mo")`)
- Samakan tanggal (inner join on Date)
- Hitung **Stock Return**: `(Close[today] - Close[t-63]) / Close[t-63] * 100`
- Hitung **IHSG Return**: sama untuk IHSG
- **RS = Stock Return - IHSG Return** (selisih return, bukan rasio)
- Jika RS > 5: "Outperforming"
- Jika RS < -5: "Underperforming"
- Selainnya: "Neutral"

**Contoh return:**
```python
{
    "stock_code": "BBCA",
    "stock_return_pct": 8.5,
    "ihsg_return_pct": 2.1,
    "rs_value": 6.4,
    "rs_status": "Outperforming",
    "period_days": 63,
    "last_updated": "2026-06-05T09:00:00"
}
```

### Fungsi 2: `calculate_all_relative_strength() -> dict`

**Logic:**
- Loop semua saham di `STOCK_LIST` (dari `stock_service`)
- Panggil `calculate_relative_strength()` untuk masing-masing
- Kategorikan:
  - `outperformers`: RS > 5, sorted DESC
  - `underperformers`: RS < -5, sorted ASC
  - `neutral`: sisanya
- Return summary

---

## Bagian C: Endpoint API Baru

### Modifikasi: `app/api/routes.py`

Tambah 3 endpoint baru:

### 1. `GET /api/ihsg`
Panggil `IHSGService.get_ihsg_summary()`

**Response:**
```json
{
    "status": "ok",
    "data": { "...semua field dari get_ihsg_summary()..." }
}
```

### 2. `GET /api/relative-strength/{code}`
Parameter path: `code` (string, contoh: "BBCA")
Panggil `calculate_relative_strength(code)`

**Response:**
```json
{
    "status": "ok",
    "data": { "...semua field dari calculate_relative_strength()..." }
}
```

### 3. `GET /api/market-breadth`
Panggil `calculate_all_relative_strength()`

**Response:**
```json
{
    "status": "ok",
    "data": {
        "outperformers": [{"code": "BBCA", "rs": 6.4, ...}, ...],
        "underperformers": [...],
        "neutral_count": 10,
        "total_analyzed": 25
    }
}
```

---

## Bagian D: Testing

### File Baru: `tests/test_ihsg_service.py`

Buat test sederhana:
1. Test `fetch_ihsg_data()` — panggil beneran, assert return `pd.DataFrame` dengan kolom valid
2. Test `get_ihsg_summary()` — assert semua key di return
3. Test `calculate_relative_strength("BBCA")` — assert return valid, RS value angka

**Catatan:** Karena panggil API beneran, test mungkin lambat. Tambah timeout 30s.

---

## Kriteria Selesai

- [ ] `ihsg_service.py` selesai, bisa ambil data IHSG
- [ ] `relative_strength.py` selesai, RS bisa dihitung
- [ ] 3 endpoint API jalan & return JSON valid
- [ ] Test file bisa jalan tanpa error
- [ ] Data IHSG muncul sebagai grafik overlay di dashboard (manual tes via browser)
- [ ] `python run.py` gak error

---
