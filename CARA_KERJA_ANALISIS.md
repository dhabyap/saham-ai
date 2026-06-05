# Cara Kerja Analisis & Rekomendasi Saham

## Alur Lengkap: Dari Data hingga Rekomendasi BUY/HOLD/SELL

```
Request (API/Telegram/Web)
        │
        ▼
  AnalysisService.analyze_stock("BBCA")
        │
        ▼
  StockService.get_latest_data("BBCA")
        │
        ▼
  Yahoo Finance API (query1.finance.yahoo.com)
  Mengambil data historis: Open, High, Low, Close, Volume
        │
        ▼
  Hitung Technical Indicators:
  ┌────────────────────────────────────────────┐
  │ MA20   → Simple Moving Average 20 hari     │
  │ MA50   → Simple Moving Average 50 hari     │
  │ RSI(14)→ Relative Strength Index           │
  │ MACD   → Moving Average Convergence/Div.   │
  │ Volume MA → Rata-rata volume 20 hari       │
  │ Pivot, S1, R1 → Support & Resistance       │
  └────────────────────────────────────────────┘
        │
        ▼
  Interpretasi Indikator:
  • Trend: Bullish / Bearish / Sideways
  • MACD: Golden Cross / Death Cross / Bullish / Bearish
  • RSI: Overbought (>70) / Normal / Oversold (<30)
  • Volume Spike (>1.5x normal)
  • Near Support / Near Resistance
        │
        ▼
  ┌──────────────────────────────────────┐
  │          DUA JALUR ANALISIS           │
  │                                      │
  │  JALUR A                  JALUR B    │
  │  (AI/LLM)                 (Rule-Based)│
  │  ┌──────────┐            ┌──────────┐ │
  │  │ Local AI │            │ Scoring  │ │
  │  │ Provider │            │ Engine   │ │
  │  └──────────┘            └──────────┘ │
  └──────────────────────────────────────┘
        │
        ▼
  Rekomendasi: BUY / HOLD / SELL
  Confidence: 0-100%
  Reasoning: Penjelasan lengkap
        │
        ▼
  Simpan ke Database (ai_predictions)
        │
        ▼
  Kirim ke:
  • API → JSON response
  • Telegram → Markdown + Chart
  • Dashboard → HTML
```

---

## Jalur A: Analisis dengan AI (Local LLM)

### Cara Kerja:

1. **Cek Cache** — Sistem cek dulu apakah analisis saham ini sudah pernah dilakukan hari ini. Kalau ada, langsung pakai hasil lama (biar cepat dan hemat).

2. **Buat Prompt** — Data indikator diubah jadi teks perintah:
   ```
   "Analisa BBCA: Harga Rp10.000 (+1,23%),
    RSI 45 (Normal), MACD Bullish, Trend Bullish,
    MA20 Rp9.800, MA50 Rp9.500,
    Support Rp9.600, Resistance Rp10.200,
    Volume 1,5x normal, Strategy swing, Risk moderate."
   ```

3. **Tambahkan Pengetahuan** — Dari knowledge base, sistem nambahi definisi dan aturan trading (misal: "RSI > 70 = overbought, berpotensi koreksi").

4. **Kirim ke Local AI** — Prompt dikirim ke OpenAI-compatible server lokal (default: `http://localhost:20128/v1`). LLM memproses dan ngasih jawaban JSON:
   ```json
   {
     "trend": "bullish",
     "recommendation": "BUY",
     "confidence": 78,
     "reasoning": "RSI normal dengan MACD bullish..."
   }
   ```

5. **Normalisasi** — Hasil dari AI dibersihkan dan dipastikan formatnya sesuai.

6. **Cache & Simpan** — Hasil disimpan di cache (biar cepat) dan database (biar permanen).

### Kelebihan:
- Analisis lebih natural dan kontekstual
- Bisa menangkap pola kompleks
- Reasoning lebih manusiawi

### Kekurangan:
- Butuh LLM server berjalan (resource berat)
- Lebih lambat (beberapa detik)
- Tergantung kualitas model

---

## Jalur B: Analisis Rule-Based (Scoring Engine)

Kalau AI tidak tersedia, sistem pake mesin scoring berbasis bobot indikator.

### Cara Kerja:

Setiap indikator dikasih skor berdasarkan kondisinya, lalu dikalikan dengan bobot:

| Indikator | Kondisi | Skor Dasar |
|-----------|---------|-----------|
| **RSI** | Oversold (<30) | +2 |
| | Overbought (>70) | -2 |
| | Normal | +0.5 |
| **Trend** | Bullish | +2 |
| | Bearish | -2 |
| | Sideways | 0 |
| **MACD** | Golden Cross | +2 |
| | Death Cross | -2 |
| | Bullish | +1 |
| | Bearish | -1 |
| **Volume** | Spike (>1.5x) | +1.5 |
| **Support/Resistance** | Dekat Support | +1.5 |
| | Dekat Resistance | -1.5 |

### Penentuan Signal:

Total skor dibandingkan dengan threshold berdasarkan risk level:

| Risk Level | Threshold | Keterangan |
|------------|-----------|------------|
| Conservative | 3.0 | Hanya BUY/SELL kalau sinyal kuat |
| Moderate | 2.0 | Default |
| Aggressive | 1.5 | Lebih sering ambil posisi |

- **Skor ≥ threshold** → **BUY**
- **Skor ≤ -threshold** → **SELL**
- **Selain itu** → **HOLD**

### Confidence:
```
confidence = 50 + (skor × 8)
dibatasi: min(1), max(99)
```

Contoh: Skor +2.5 → Confidence = 50 + 20 = 70%

---

## Sumber Data Saham

Saham diambil dari **Yahoo Finance** (`query1.finance.yahoo.com`) dengan kode IDX (+ `.JK`):
- BBCA, BBRI, BMRI, BBNI (Banking)
- TLKM, EXCL, TOWR (Telekomunikasi)
- ASII, UNVR, HMSP, GGRM, INDF (Consumer)
- ADRO, ITMG, PTBA (Energy/Batubara)
- CPIN, KLBF, ICBP, JSMR, PGAS
- SMGR, INTP, SMMA, AKRA, MEDC

Total: **25 saham IDX** (hardcoded di `STOCK_LIST`).

---

## Indikator Teknikal yang Digunakan

| Indikator | Parameter | Fungsi |
|-----------|-----------|--------|
| **MA20** | 20 periode | Tren jangka pendek |
| **MA50** | 50 periode | Tren jangka menengah |
| **RSI** | 14 periode | Mengukur overbought/oversold |
| **MACD** | 12, 26, 9 | Momentum & kekuatan tren |
| **Volume MA** | 20 periode | Deteksi volume spike |
| **Pivot Point** | H+L+C/3 | Support & Resistance |

---

## Strategi Trading

| Strategy | Threshold Scoring | Cocok Untuk |
|----------|-------------------|-------------|
| **Scalping** | 1.0 | Intraday, profit kecil cepat |
| **Swing** | 2.0 | Hold 1-7 hari (default) |
| **Long Term** | 3.0 | Hold mingguan-bulanan |

---

## ML Training (Fitur Tambahan)

Sistem juga bisa **melatih model Machine Learning** (Random Forest, XGBoost, LightGBM) dari data historis untuk meningkatkan akurasi prediksi.

Cara:
1. Ambil 6 bulan data historis
2. Hitung 11 fitur (RSI, MACD, MA, Volume, dll)
3. Label: +1 (return >2%), -1 (return <-2%), 0 (stagnan)
4. Train model
5. Backtest untuk evaluasi
6. Auto-adjust bobot indikator berdasarkan performa

---

## Ringkasan Output

Setelah analisis selesai, kamu bakal dapet:

```
Saham: BBCA (Bank Central Asia)
Harga: Rp10.000 (+1,23%)
RSI: 45 (Normal)
MACD: Bullish
Trend: Bullish
Support: Rp9.600 | Resistance: Rp10.200
Volume: 1,5x normal (spike)

✅ REKOMENDASI: BUY
🎯 Confidence: 78%
💡 Alasan: RSI normal dengan MACD bullish,
    harga di atas MA20 dan MA50, tren menguat.
```

> **Disclaimer:** Ini alat bantu analisis, bukan jaminan profit. Selalu DYOR (Do Your Own Research)!
