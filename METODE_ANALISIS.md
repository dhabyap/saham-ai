# Metode Analisis Saham — Money Flow & Accumulation Centric

## Filosofi

**"Harga mengikuti uang."**

Indikator teknikal (RSI, MACD, MA) bukan lagi faktor utama. Analisis berpusat pada:

1. Foreign Flow
2. Institutional Flow
3. Accumulation
4. Distribution
5. Relative Strength
6. Sector Rotation
7. Volume Analysis

Teknikal hanya sebagai konfirmasi (bobot maksimal 5%).

---

## Dua Model Analisis

### 1. Day Trading — Beli Pagi Jual Sore

**Tujuan:** Profit dari pergerakan intraday.

**Fokus:**
- Opening drive (30 menit pertama)
- Volume spike pagi hari
- Foreign net buy pagi
- Tick index & short-term momentum
- Support/resistance level intraday

**Entry:**
- Volume pagi > 1.5x rata-rata
- Foreign buy mendominasi
- Harga breakout opening range

**Exit:**
- Target profit 1-3%
- Cut loss 0.5-1%
- Pukul 14:30 evaluasi posisi

**Risk:**
- Hanya saham likuid
- Strict cut loss
- Tidak untuk saham gorengan

---

### 2. Akumulasi Asing — Swing to Long Term

**Tujuan:** Menangkap akumulasi institusi/asing.

**Fokus:**
- Foreign net buy harian & kumulatif
- Broker summary (buy side vs sell side)
- Harga sideways diiringi volume naik
- Supply terserap tanpa koreksi berarti
- Relative strength vs IHSG

**Entry:**
- Akumulasi asing 5+ hari berturut
- Volume meningkat, harga stabil
- IHSG koreksi tapi saham ini kuat

**Exit:**
- Distribusi asing mulai
- Breakdown support akumulasi
- Target berdasarkan akumulasi zone

---

## Bobot Scoring

| Komponen | Bobot |
|----------|-------|
| Foreign Flow | 35% |
| Accumulation / Distribution | 25% |
| Relative Strength | 15% |
| Sector Rotation | 10% |
| Volume Analysis | 10% |
| Technical Confirmation | 5% |

---

## Level Prioritas Analisis

### Level 1 — Money Flow (Bobot Tertinggi)

**Pertanyaan utama:** *"Apakah ada uang besar yang masuk?"*

**Data:**
- Foreign Net Buy / Sell
- Foreign Accumulation / Distribution
- Local Institution Accumulation
- Smart Money Flow (broker summary)
- Transaksi besar (block trade)

**Jika ya:** Bullish Score meningkat signifikan.

**Jika tidak:** Waspada, jangan entry hanya karena teknikal bagus.

---

### Level 2 — Akumulasi

**Deteksi:**
- Harga sideways / konsolidasi
- Volume meningkat
- Foreign net buy positif
- Supply terserap (harga tidak turun walau ada tekanan jual)

**Kondisi:**
Jika selama beberapa hari:
- Foreign Buy meningkat
- Harga tidak turun

**Label:** `AKUMULASI`

**Contoh reasoning:**
> "Terjadi akumulasi asing selama 5 hari dengan net buy 250M sementara harga tetap stabil. Menunjukkan adanya penyerapan supply oleh smart money."

---

### Level 3 — Distribusi

**Deteksi:**
- Foreign net sell
- Harga gagal naik
- Volume besar saat merah
- Breakdown support

**Label:** `DISTRIBUSI`

---

### Level 4 — Relative Strength

**Bandingkan dengan:**
- IHSG
- Sektor terkait

**Contoh:**
- IHSG: -1.7%
- BBCA: +0.5%
- **Relative Strength = STRONG**

**Kesimpulan:**
BBCA lebih kuat dari market, ada yang nahan.

---

### Level 5 — Sector Rotation

**Pantau sektor:**
- Banking
- Energy
- Coal
- Property
- Technology
- Consumer
- Healthcare
- Infrastructure

**Cari:** Sektor mana yang mendapat aliran dana terbesar.

Jika sektor sedang diakumulasi, naikkan score saham dalam sektor tersebut.

---

### Level 6 — Unusual Volume

**Deteksi:**
Volume > 1.5x rata-rata

Jika disertai:
- Foreign buy
- Breakout

**Label:** Bullish kuat

---

### Level 7 — Teknikal (Konfirmasi Saja)

**Indikator:**
- RSI (14)
- MACD (12, 26, 9)
- MA20 & MA50

**Peran:** Hanya sebagai konfirmasi. Bukan penentu utama.

**Bobot maksimal:** 5-20%

---

## Format Output Baru

```
BBCA
Harga:           Rp 9.850

Market Context:
  IHSG:          -1.7%

Money Flow Analysis:
  Foreign Net Buy:  +463.7 Miliar
  Status:           AKUMULASI (5 hari)
  Broker:           Mandiri Sekuritas +120M

Relative Strength:  STRONG

Sektor:             BANKING
  Sector Flow:      POSITIVE

Volume:             1.8x Average

Technical:
  RSI:              62
  MACD:             Bullish
  MA20/50:          Bullish

Kesimpulan:
  BBCA menunjukkan akumulasi institusi dan foreign flow
  positif ketika IHSG mengalami koreksi tajam.
  Terjadi penyerapan supply oleh smart money.

Recommendation:   BUY
Confidence:       88%
Risk:             Medium
Target:           Rp 10.300
Invalidation:     Rp 9.500

---

### Alternatif Output — Model Day Trading

```
BBCA (Day Trading)
Harga:           Rp 9.850

Opening Drive:   +0.8% (30 menit pertama)
Volume:          2.1x rata-rata (pagi)

Money Flow:
  Foreign Buy:     +85 Miliar (pagi ini)
  Domestik:        Netral

Level:
  Support I:       Rp 9.800
  Resistance I:    Rp 9.950

Momentum:         Positif
Risk/Reward:      1:2.5

Rebounds:         BUY
  Entry:          Rp 9.850
  Target:         Rp 9.950
  Cut Loss:       Rp 9.780
Confidence:       75%
```

---

## Cara Berpikir AI

### Harus seperti:
- ✓ Bandar yang mengikuti uang besar
- ✓ Smart money tracker
- ✓ Institutional flow analyst
- ✓ Melihat siapa yang membeli sebelum memberikan rekomendasi

### BUKAN seperti:
- ✗ Scanner RSI
- ✗ Scanner MACD
- ✗ Scanner indikator retail

### Pertanyaan Kunci Sebelum Rekomendasi:

**"Siapa yang sedang membeli saham ini?"**

Jika jawabannya foreign institution → BUY
Jika retail ramai tapi asing jual → HOLD/SELL
Jika tidak ada uang besar masuk → SKIP

---

## Sumber Data yang Diperlukan

| Data | Sumber |
|------|--------|
| Foreign Net Buy/Sell | RTI / Bursa Efek Indonesia |
| Broker Summary | RTI / Stockbit |
| IHSG | Yahoo Finance |
| Harga & Volume | Yahoo Finance |
| Sektor | Mapping manual |
| Block Trade | BEI |

---

## Status Label

| Label | Kondisi |
|-------|---------|
| AKUMULASI | Foreign buy + harga stabil |
| DISTRIBUSI | Foreign sell + harga gagal naik |
| NETRAL | Foreign netral / mixed |
| RELATIVE STRONG | Outperform IHSG |
| RELATIVE WEAK | Underperform IHSG |
| UNUSUAL VOLUME | Volume > 1.5x rata-rata |
| SECTOR INFLOW | Sektor dapat aliran dana |
| SECTOR OUTFLOW | Sektor keluar dana |

---

> **Catatan:** Filosofi ini menggeser analisis dari indikator retail ke institutional flow analysis. Semua data foreign flow dan broker summary harus diambil dari sumber eksternal (RTI, BEI, Stockbit) karena tidak tersedia di Yahoo Finance.
