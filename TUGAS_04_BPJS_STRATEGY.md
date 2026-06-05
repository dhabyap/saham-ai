# Tugas 4: BPJS Day Trading Strategy

## Target

Implementasi **"Beli Pagi Jual Sore"** — strategi day trading intraday dengan entry pagi hari, exit sebelum market tutup (14:30 WIB/16:00 WIB IDX). Target profit 1-3%, cut loss 0.5-1%.

---

## Strategi Dasar

```
1. Pre-market (08:30-09:00): Cek gap, foreign flow kemarin, news
2. Opening range (09:00-09:30): Deteksi breakout 30 menit pertama
3. Entry: Breakout opening range + volume spike + foreign buy
4. Exit: Target profit 1-3% ATAU cut loss 0.5-1% ATAU pukul 14:30 evaluasi
```

---

## Arsitektur

```
stock_service (intraday data) ──→ BPJSStrategy ──→ ScoringEngine ──→ AnalysisService
foreign_flow (hari sebelumnya) ──→                        ↑
ihsg_service (IHSG intraday) ──→──────────────────────────┘
```

---

## Bagian A: Intraday Data Helper

### Modifikasi: `app/services/stock_service.py`

### Fungsi baru: `fetch_intraday_data(code: str, interval: str = "5m", period: str = "2d") -> Optional[pd.DataFrame]`

**Logic:**
- Sama seperti `fetch_stock_data()` tapi pake interval intraday
- Interval valid: "1m", "2m", "5m", "15m", "30m", "60m"
- **Catatan:** Yahoo Finance intraday terbatas (biasanya 7 hari untuk 5m data)
- Return format sama: DataFrame dengan Open, High, Low, Close, Volume
- Fallback: Jika intraday gagal (rate limited), return daily data + log warning

```python
def fetch_intraday_data(code: str, interval: str = "5m", period: str = "2d") -> Optional[pd.DataFrame]:
    """Fetch intraday stock data from Yahoo Finance.
    
    Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h
    Max periods depends on interval:
    - 1m: max 7 days
    - 5m: max 60 days
    - 15m+: max 60 days
    """
```

### Fungsi baru: `get_opening_range(df: pd.DataFrame) -> dict`

**Logic:**
- Ambil 30 menit pertama dari data intraday (atau 3 baris pertama untuk 5m interval)
- Hitung:
  - `open_range_high`: High tertinggi di opening range
  - `open_range_low`: Low terendah di opening range
  - `open_range_mid`: (high + low) / 2
  - `range_size`: high - low (dalam rupiah)
  - `range_pct`: range_size / open * 100
  - `gap_pct`: (open hari ini - close kemarin) / close kemarin * 100

```python
{
    "open_range_high": 10250,
    "open_range_low": 10175,
    "open_range_mid": 10212.5,
    "range_size": 75,
    "range_pct": 0.74,
    "gap_pct": 0.25,
    "gap_type": "gap_up"  # "gap_up", "gap_down", "no_gap"
}
```

### Fungsi baru: `calculate_intraday_volume_profile(df: pd.DataFrame) -> dict`

**Logic:**
- Bandingkan volume 15 menit pertama vs rata-rata per 15 menit
- Deteksi volume spike intraday
- Hitung:
  - `first_15min_volume`: Volume 15 menit pertama
  - `avg_15min_volume`: Rata-rata volume per 15 menit (keseluruhan hari)
  - `volume_ratio_15m`: first_15min_volume / avg_15min_volume
  - `volume_spotted`: True jika > 1.5x

---

## Bagian B: BPJS Strategy Engine

### File Baru: `app/ai/strategies/bpjs_strategy.py`

```python
from datetime import datetime, time
from typing import Optional, Literal
from dataclasses import dataclass

BPJSAction = Literal["ENTER", "EXIT", "HOLD", "WAIT"]
BPJSResult = Literal["TP_HIT", "CL_HIT", "MANUAL_EXIT", "TIME_EXIT", "HOLDING"]
```

### @dataclass BPJSSignal

```python
@dataclass
class BPJSSignal:
    action: BPJSAction            # ENTER, EXIT, HOLD, WAIT
    stock_code: str
    entry_price: Optional[float]  # harga entry (jika ENTER)
    target_profit: Optional[float]  # harga TP
    cut_loss: Optional[float]     # harga CL
    current_price: Optional[float]
    reason: str                   # penjelasan signal
    confidence: float             # 0-100
    open_range: Optional[dict]
    volume_analysis: Optional[dict]
    score_details: Optional[dict]
    timestamp: str
```

### Fungsi 1: `analyze_pre_market(code: str) -> dict`

**Logic:**
Analisis sebelum market buka (08:30-09:00 WIB):
- Cek gap dari harga close kemarin vs open hari ini
- Cek foreign flow kemarin (dari foreign_flow table)
- Cek IHSG pagi ini (gap IHSG)
- Cek news sentimen (rule-based: jika ada berita besar, flagged)
- Return dict dengan semua info di atas

### Fungsi 2: `calculate_entry_signal(code: str) -> Optional[BPJSSignal]`

**Logic:**
Dipanggil antara 09:00-12:00 WIB:

**Kondisi ENTER (semua HARUS terpenuhi):**
1. ✅ Harga **breakout opening range high** (close > open_range_high)
2. ✅ Volume 15 menit pertama > 1.5x rata-rata
3. ✅ Foreign flow kemarin NET BUY (data dari Tugas 2)
4. ✅ IHSG tidak gap down > 1%
5. ✅ **Tidak oversold/overbought ekstrim** (RSI > 20 dan < 80)
6. ✅ Likuid (volume > threshold)

**Kalau ENTER:**
- Entry price: harga saat ini + 0.1% (buffer)
- Target profit: entry + 1.5% (atau sesuai risk/reward 1:2)
- Cut loss: entry - 0.7% (atau di bawah opening range low)
- Hitung R:R (risk/reward ratio), HARUS > 1:2

**Kondisi TIDAK ENTER:**
- Jika gap up > 3% → "Gap terlalu besar, risiko reversal"
- Jika gap down > 2% → "Gap down terlalu dalam, tunggu konfirmasi"
- Jika volume < 1.5x → "Volume tidak cukup"
- Jika foreign net sell kemarin → "Asing jual, hindari"

### Fungsi 3: `calculate_exit_signal(code: str, entry_price: float, tp: float, cl: float, entry_time: datetime) -> BPJSSignal`

**Logic:**
Dipanggil terus selama posisi terbuka:

| Kondisi | Action | Priority |
|---------|--------|----------|
| Harga >= TP | EXIT (Target Profit) | Tertinggi |
| Harga <= CL | EXIT (Cut Loss) | Tertinggi |
| Sekarang >= 14:30 WIB | EXIT (Time Exit) | Tinggi |
| Harga turun 0.3% dalam 5 menit + volume | EXIT (Momentum hilang) | Medium |
| Selainnya | HOLD | Rendah |

### Fungsi 4: `get_scoring_recommendation(code: str, df: pd.DataFrame) -> BPJSSignal`

**Logic:**
1. Ambil data intraday
2. Ambil foreign flow kemarin
3. Analisis pre-market
4. Analisis opening range
5. Kalkulasi entry signal
6. Return BPJSSignal dengan action + detail

---

## Bagian C: Integrasi ke Analysis Service

### Modifikasi: `app/services/analysis_service.py`

Di method `analyze_stock()`, jika strategy = "day_trade":
1. Panggil `BPJSStrategy.get_scoring_recommendation()`
2. Return BPJS signal sebagai bagian dari response

Atau buat method terpisah:
```python
def analyze_day_trade(self, code: str) -> dict:
    """Analisis spesifik untuk day trading BPJS."""
    strategy = BPJSStrategy()
    signal = strategy.get_scoring_recommendation(code, df)
    # Combine dengan scoring engine
    scoring = ScoringEngine()
    score = scoring.calculate_score(code, strategy="day_trade", risk_level="high")
    return {
        "signal": signal,
        "scoring": score,
        "recommendation": signal.action,
    }
```

---

## Bagian D: Endpoint API Baru

### Modifikasi: `app/api/routes.py`

### `GET /api/day-trade/{code}`
Analisis day trading BPJS untuk satu saham.

### `GET /api/day-trade/watchlist`
Cek semua saham yang punya potensi day trading hari ini.
- Filter: breakout opening range + volume spike + foreign buy kemarin
- Return list kandidat, sorted by confidence DESC

---

## Bagian E: Monitoring

### File Baru: `app/services/bpjs_monitor.py`

### Fungsi: `monitor_open_positions()`

**Logic:**
- Cek posisi yang masih terbuka setiap 15 menit
- Update TP/CL
- Kirim notifikasi (print/log) jika ada exit signal

---

## Bagian F: Testing

### File Baru: `tests/test_bpjs_strategy.py`

1. Test `fetch_intraday_data("BBCA")` — assert return DataFrame
2. Test `get_opening_range()` dengan data mock
3. Test `calculate_entry_signal()` dengan kondisi ideal → action = "ENTER"
4. Test `calculate_entry_signal()` tanpa volume spike → action = "WAIT" atau "HOLD"
5. Test `calculate_exit_signal()` saat harga > TP → action = "EXIT"

---

## Kriteria Selesai

- [ ] `fetch_intraday_data()` bisa ambil data 5m dari Yahoo Finance
- [ ] `get_opening_range()` kalkulasi opening range akurat
- [ ] `BPJSStrategy.calculate_entry_signal()` return ENTER hanya jika kondisi terpenuhi
- [ ] Exit logic handle TP, CL, dan time exit
- [ ] Endpoint `/api/day-trade/{code}` return signal
- [ ] Endpoint `/api/day-trade/watchlist` return kandidat hari ini
- [ ] Integrasi ke analysis service untuk strategy="day_trade"
- [ ] Test file jalan

---
