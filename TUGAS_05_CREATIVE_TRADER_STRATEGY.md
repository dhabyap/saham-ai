# Tugas 5: Creative Trader Long Term Strategy

## Target

Implementasi strategi **swing to long term** dengan fokus akumulasi asing/institusi, seperti pendekatan Creative Trader Channel. Hold dari minggu ke bulan, target capital gain dividen.

---

## Strategi Dasar

```
1. Cari saham dengan akumulasi asing 5+ hari berturut-turut
2. Validasi: harga sideways dengan volume meningkat (supply terserap)
3. Relatif kuat terhadap IHSG (IHSG turun, saham ini tetap)
4. Masuk saat koreksi kecil di tengah tren akumulasi
5. Exit saat distribusi asing mulai ATAU breakdown support akumulasi
```

---

## Arsitektur

```
foreign_flow (Tugas 2) ──→ AccumulationAnalyzer ──→ CreativeTraderStrategy
ihsg_service (Tugas 1)  ──→ RelativeStrength  ───→           │
stock_service            ──→ Technical                ───────→│
                                                              ↓
                                                     ScoringEngine + AnalysisService
```

---

## Bagian A: Accumulation Analyzer

### File Baru: `app/ai/strategies/creative_trader_strategy.py`

### Fungsi 1: `analyze_accumulation_phase(stock_code: str) -> dict`

**Logic:**
Analisis fase akumulasi berdasarkan data foreign flow + harga:

```python
def analyze_accumulation_phase(stock_code: str, lookback_days: int = 60) -> dict:
```

**Cek 1 — Akumulasi Kuantitatif (dari foreign_flow):**
- `accumulation_days`: berapa hari net buy berturut-turut (dari Tugas 2)
- `cumulative_net_20d`: total net buy 20 hari
- `avg_net_10d`: rata-rata net buy per hari 10 hari
- `net_buy_ratio`: persentase hari net buy dalam 20 hari terakhir
- Jika accumulation_days >= 5: **Fase Akumulasi Aktif**
- Jika accumulation_days >= 3 + net_buy_ratio >= 60%: **Fase Akumulasi Awal**

**Cek 2 — Harga Sideways + Volume Naik (Supply Terserap):**
- Hitung `price_range_20d`: (highest high - lowest low) / lowest low * 100
- Hitung `volume_trend_20d`: slope volume 20 hari (positif = meningkat)
- Hitung `price_trend_20d`: slope harga 20 hari
- Jika price_range_20d < 5% + volume_trend positif: **Supply terserap**
- Jika price_range_20d < 5% + volume_trend positif + price_trend negatif: **Akumulasi tersembunyi** (harga turun tipis tapi volume naik — institusi narik)

**Cek 3 — Relative Strength vs IHSG (dari Tugas 1):**
- Panggil `calculate_relative_strength(stock_code)`
- Require RS > 0 (outperforming atau minimal tidak underperforming)

**Return:**
```python
{
    "stock_code": "BBCA",
    "accumulation_days": 7,
    "cumulative_net_20d": 350000000000,  # Rp 350 M net buy 20 hari
    "net_buy_ratio": 75,  # 75% hari net buy
    "phase": "active_accumulation",  # "active_accumulation", "early_accumulation", "distribution", "neutral"
    "supply_absorbed": True,
    "hidden_accumulation": False,
    "price_range_20d": 3.5,  # %
    "volume_trend": "increasing",
    "relative_strength": {
        "rs_value": 4.2,
        "rs_status": "Outperforming"
    },
    "avg_entry_zone": {
        "upper": 10400,  # harga wajar atas
        "lower": 9900,   # harga wajar bawah
        "current_position": "mid",  # "near_upper", "near_lower", "mid"
    },
    "confidence": 78,  # 0-100
    "summary": "BBCA dalam fase akumulasi aktif 7 hari net buy...",
    "last_updated": "2026-06-05T09:00:00"
}
```

**Fungsi untuk kalkulasi avg_entry_zone:**
- `avg_entry_zone.upper`: harga rata-rata + 1 standard deviasi selama akumulasi
- `avg_entry_zone.lower`: harga rata-rata - 1 standard deviasi selama akumulasi
- Jika current_price di lower zone → "good entry point"
- Jika current_price di upper zone → "wait for pullback"

---

## Bagian B: Entry & Exit Rules

### Fungsi 2: `calculate_entry_point(stock_code: str) -> dict`

**Logic:**

**Kondisi ENTRY (semua HARUS terpenuhi):**
1. ✅ Fase akumulasi aktif (accumulation_days >= 5)
2. ✅ Supply terserap (harga sideways + volume naik)
3. ✅ Relative strength POSITIF (RS > 0)
4. ✅ Harga di **lower zone** atau **mid zone** (jangan beli di upper akumulasi)
5. ✅ Cut loss terdefinisi (support level jelas)

**Rekomendasi Entry:**
```python
{
    "action": "BUY" / "WAIT" / "ACCUMULATE",
    "entry_type": "lumpsum" / "dca",  # lumpsum kalo lower zone, dca kalo mid zone
    "entry_price": 9950,
    "suggested_entry_range": {
        "ideal": 9950,
        "max": 10100,
        "min": 9700
    },
    "stop_loss": 9500,    # di bawah support akumulasi
    "target_profit": {
        "short_term": 10600,   # 6-7% (untuk swing 1-2 minggu)
        "medium_term": 11500,  # 15%+ (untuk long term 1-3 bulan)
    },
    "position_sizing": "normal",  # "aggressive" kalo lower zone, "normal" kalo mid
    "risk_pct": 2.5,  # risiko per trade dalam % dari modal
}
```

**Kondisi WAIT:**
- Jika accumulation_days < 3: "Akumulasi belum cukup"
- Jika harga di upper zone: "Tunggu pullback ke support akumulasi"
- Jika RS negatif: "Relative strength negatif, saham underperforming IHSG"

### Fungsi 3: `calculate_exit_point(stock_code: str, entry_price: float) -> dict`

**Logic:**

**Kondisi EXIT:**

| Kondisi | Action |
|---------|--------|
| Distribusi asing 3+ hari berturut-turut | SELL |
| Harga breakdown support akumulasi (-5% dari entry) | SELL (cut loss) |
| Relative strength jadi negatif + volume turun | SELL (momentum hilang) |
| Target tercapai (15%+ untuk long term) | SELL sebagian / TRAILING STOP |
| IHSG koreksi > 5% + saham ikut turun | SELL (market risk) |
| Foreign flow reversal (net sell kumulatif) | SELL |

```python
{
    "action": "HOLD" / "SELL" / "SELL_HALF" / "TRAILING_STOP",
    "current_price": 10800,
    "entry_price": 9950,
    "profit_pct": 8.5,
    "reason": "Distribusi asing 3 hari...",
    "suggested_stop": 10200,  # trailing stop
    "signals_triggered": [
        "Foreign distribution 3 hari berturut-turut",
        "Harga breakdown support MA50"
    ],
    "urgency": "high",  # "immediate", "high", "normal", "low"
}
```

- **SELL**: Exit penuh, urgency high
- **SELL_HALF**: Jual 50%, sisanya pake trailing stop
- **TRAILING_STOP**: Pindahkan stop loss ke harga lebih tinggi (lock profit)
- **HOLD**: Belum ada sinyal exit

---

## Bagian C: Multi-Timeframe Analysis

### Fungsi 4: `multi_timeframe_analysis(stock_code: str) -> dict`

**Logic:**
Analisis 3 timeframe untuk konfirmasi tren:

| Timeframe | Periode | Fokus |
|-----------|---------|-------|
| **Weekly** | 52 minggu | Trend utama, MA50/MA200, support/resistance besar |
| **Daily** | 6 bulan | Entry timing, MACD, RSI, volume, foreign flow |
| **Intraday (60m)** | 5 hari | Short-term momentum, pullback entry |

**Cek:**

**Weekly:**
- Close > MA50 weekly? → Uptrend jangka panjang
- MA50 > MA200 weekly? → Golden cross jangka panjang (bullish)
- Volume mingguan meningkat 3 minggu? → Akumulasi

**Daily + Foreign Flow (dari fungsi 1 & 2 di atas)**

**Intraday (60m):**
- Koreksi intraday? → Entry point
- Volume spike intraday dengan harga turun? → Distribusi intraday

**Return:**
```python
{
    "weekly_outlook": "Bullish",
    "daily_phase": "Akumulasi Aktif",
    "intraday_momentum": "Koreksi ringan",
    "alignment": "ALIGNED" / "WARNING" / "CONFLICT",
    # ALIGNED = semua timeframe setuju
    # WARNING = daily ok, weekly bearish
    # CONFLICT = timeframe conflict, skip trade
}
```

---

## Bagian D: Screening / Watchlist

### Fungsi 5: `scan_for_long_term_candidates() -> list[dict]`

**Logic:**
Loop semua saham di STOCK_LIST, cari yang:
1. Accumulation_days >= 3 (dari foreign_flow)
2. RS > 0 (dari relative_strength)
3. Supply terserap (harga sideways + volume naik)
4. Setidaknya 1: weekly dalam uptrend

Return list kandidat, sorted by confidence DESC.

---

## Bagian E: Integrasi

### Modifikasi: `app/services/analysis_service.py`

Jika strategy = "swing" atau "long_term":
1. Panggil `CreativeTraderStrategy.multi_timeframe_analysis(code)`
2. Panggil `ScoringEngine.calculate_score(code, strategy="long_term")`
3. Kombinasikan hasilnya

### Modifikasi: `app/api/routes.py`

### `GET /api/long-term/{code}`
Analisis long term untuk satu saham.

### `GET /api/long-term/candidates`
List semua saham yang jadi kandidat long term, sorted by confidence.

**Response:**
```json
{
    "status": "ok",
    "data": {
        "candidates": [
            {
                "code": "BBCA",
                "name": "PT Bank Central Asia Tbk",
                "accumulation_days": 7,
                "rs_value": 4.2,
                "phase": "active_accumulation",
                "entry_zone": {"lower": 9900, "upper": 10400, "current": 10250},
                "confidence": 78,
                "score": 72.5
            }
        ],
        "total_analyzed": 25,
        "last_updated": "2026-06-05T09:00:00"
    }
}
```

---

## Bagian F: Dashboard Integration

### Modifikasi: `app/static/dashboard.js`

Tambah section baru di dashboard:
- **Top Long Term Candidates** — 5 kandidat terbaik (dari `/api/long-term/candidates`)
- **Accumulation Heatmap** — visualisasi sektor mana yang diakumulasi asing

Ini bisa dikerjakan oleh **frontend developer** terpisah.

---

## Bagian G: Testing

### File Baru: `tests/test_creative_trader_strategy.py`

1. Test `analyze_accumulation_phase("BBCA")` — dengan mock foreign flow data
2. Test `calculate_entry_point()` — dengan data akumulasi valid → action = "BUY"
3. Test `calculate_entry_point()` — tanpa akumulasi → action = "WAIT"
4. Test `calculate_exit_point()` — dengan distribusi asing → action = "SELL"
5. Test `multi_timeframe_analysis("BBCA")` — assert return alignment
6. Test `scan_for_long_term_candidates()` — assert return list

---

## Kriteria Selesai

- [ ] `analyze_accumulation_phase()` deteksi akumulasi asing akurat
- [ ] Entry rules handle semua kondisi (BUY/WAIT/ACCUMULATE)
- [ ] Exit rules handle SELL, SELL_HALF, TRAILING_STOP
- [ ] Multi-timeframe analysis (weekly + daily + intraday)
- [ ] Screening dapet 3-5 kandidat long term
- [ ] Endpoint `/api/long-term/{code}` return analisis lengkap
- [ ] Endpoint `/api/long-term/candidates` return list
- [ ] Integrasi ke scoring engine
- [ ] Test file jalan

---
