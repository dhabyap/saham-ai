# Tugas: Bangun Halaman Dashboard Utama

## Target

Buat ulang file `app/templates/dashboard.html` menjadi halaman landing page yang:

1. **Menjelaskan APA itu website ini** — begitu orang buka langsung paham
2. **Menunjukkan semua fitur** yang tersedia
3. **Ada navigasi** ke halaman lain (AI Settings, AI Performance, Upload Analyzer)
4. **Ada data real-time** dari API yang sudah ada
5. **Tampilan profesional, dark theme** (konsisten dengan halaman lain)

---

## Arsitektur yang Ada

### Tech Stack

| Layer | Teknologi |
|-------|-----------|
| Backend | FastAPI (Python) |
| Frontend | HTML + CSS + JavaScript murni (tanpa framework JS) |
| CSS | Bootstrap 5.3.2 (CDN) + custom `style.css` |
| Icons | Bootstrap Icons 1.11.2 (CDN) |
| Charts | Chart.js 4.4.1 (CDN) |
| Data | Semua via fetch API ke endpoint REST |

### Cara Kerja

Semua halaman adalah **file HTML statis** (tidak pakai Jinja2 template). Data diambil dari API menggunakan `fetch()` JavaScript.

```
Browser → fetch('/api/...') → FastAPI → Database/Yahoo Finance → JSON → Render di HTML
```

---

## API Endpoints yang Tersedia (sudah siap tinggal pakai)

### Market Overview

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/market-summary` | GET | Ringkasan pasar: total stocks, advancing/declining, fear & greed index |
| `/api/market-sentiment` | GET | Sentimen pasar: bullish/neutral/bearish, advance-decline ratio |
| `/api/sector-performance` | GET | Performa per sektor (Banking, Energy, Coal, dll) |

### Top Movers

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/top-gainers?limit=5` | GET | Top 5 saham dengan kenaikan tertinggi |
| `/api/top-losers?limit=5` | GET | Top 5 saham dengan penurunan terbesar |
| `/api/top-volume?limit=5` | GET | Top 5 saham dengan volume tertinggi |

### Stock & Analysis

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/stocks` | GET | Daftar 25 saham IDX |
| `/api/stock/{code}?period=3mo` | GET | Data harga + indikator teknikal |
| `/api/analyze/{code}?period=3mo` | GET | Analisis lengkap + rekomendasi BUY/HOLD/SELL |
| `/api/chart/{code}` | GET | Generate chart PNG |

### AI Learning

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/learning/performance` | GET | Akurasi, winrate, avg profit |
| `/api/learning/accuracy-chart` | GET | Data history akurasi untuk chart |
| `/api/learning/predictions?limit=5` | GET | 5 prediksi terbaru |

### System

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/api/health` | GET | Health check server |
| `/api/ai/status` | GET | Status koneksi AI provider |

---

## Desain Dashboard (yang harus dibangun)

### Layout Halaman

```
┌─────────────────────────────────────────────────────────────┐
│  NAVBAR                                                      │
│  Logo | Menu: Dashboard | AI Settings | AI Perf | Upload    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─── SECTION 1: HERO / WELCOME ────────────────────────┐  │
│  │  Judul: AI Stock Analyzer Indonesia                   │  │
│  │  Subjudul: Analisis saham IDX dengan AI, real-time   │  │
│  │  data dari Yahoo Finance, Telegram Bot & Dashboard   │  │
│  │  25 saham IDX teratas | AI-powered BUY/HOLD/SELL    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 2: MARKET OVERVIEW ────────────────────────┐  │
│  │  [Fear & Greed] [Advancing] [Declining] [Unchanged]  │  │
│  │  [IHSG Change] [Total Volume]                         │  │
│  │  → Data dari /api/market-summary                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 3: TOP MOVERS ─────────────────────────────┐  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │  │ TOP      │  │ TOP      │  │ TOP      │            │  │
│  │  │ GAINERS  │  │ LOSERS   │  │ VOLUME   │            │  │
│  │  │ 1. BBCA  │  │ 1. TLKM  │  │ 1. BBRI  │            │  │
│  │  │ 2. BMRI  │  │ 2. ASII  │  │ 2. BBCA  │            │  │
│  │  └──────────┘  └──────────┘  └──────────┘            │  │
│  │  → Data dari /api/top-gainers, top-losers, top-volume  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 4: AI PERFORMANCE ─────────────────────────┐  │
│  │  [Accuracy: 72%] [Winrate: 65%] [Avg Profit: 3.2%]  │  │
│  │  [Total Predictions: 150]                              │  │
│  │  → Data dari /api/learning/performance                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 5: SECTOR PERFORMANCE ─────────────────────┐  │
│  │  Horizontal bar chart atau badge per sektor            │  │
│  │  Banking +2.3% | Energy -1.1% | Consumer +0.8%       │  │
│  │  → Data dari /api/sector-performance                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 6: RECENT PREDICTIONS ─────────────────────┐  │
│  │  Tabel: Kode | Rekomendasi | Confidence | Profit     │  │
│  │  BBCA | BUY | 85% | +2.3%                            │  │
│  │  BBRI | HOLD | 60% | -                              │  │
│  │  → Data dari /api/learning/predictions?limit=5        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 7: FITUR-FITUR ────────────────────────────┐  │
│  │  Grid kartu fitur:                                     │  │
│  │  📊 Real-time Stock Analysis | 🤖 AI Recommendations  │  │
│  │  📈 Interactive Charts | 📱 Telegram Bot              │  │
│  │  🧠 Machine Learning | ⚙️ AI Settings                 │  │
│  │  📋 Excel Upload | 📊 Performance Tracking            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── SECTION 8: STOCK LIST ─────────────────────────────┐  │
│  │  Grid/list 25 saham IDX dengan harga dan change %    │  │
│  │  Filter/search untuk cari saham                        │  │
│  │  Klik salah satu → buka halaman detail analisis      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── FOOTER ────────────────────────────────────────────┐  │
│  │  AI Stock Analyzer Indonesia v1.0.0 | DYOR            │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Detail Implementasi Per Section

### 1. NAVBAR

Navbar dark dengan menu navigasi ke semua halaman:

```
[AI Stock Analyzer]  [Dashboard] [AI Settings] [AI Performance] [Upload Analyzer]
```

Halaman **Dashboard** = `/` (file `dashboard.html`)
Halaman **AI Settings** = `/ai-settings` (file `ai_settings.html`)
Halaman **AI Performance** = `/ai-performance` (file `ai_performance.html`)
Halaman **Upload Analyzer** = `/upload-analyzer` (file `upload_analyzer.html`)

Tambahkan link ini di sidebar/navbar.

> **Catatan:** Halaman `ai_settings.html` dan `ai_performance.html` sudah punya sidebar dengan link ke Dashboard. Pastikan konsisten.

---

### 2. HERO / WELCOME SECTION

**Judul besar** dengan efek:
```html
<h1>AI Stock Analyzer Indonesia</h1>
<p>Analisis saham IDX berbasis AI dengan data real-time dari Yahoo Finance.
   Dapatkan rekomendasi BUY/HOLD/SELL, pantau market, dan optimalkan trading kamu.</p>
```

Tambahkan **stat badge**:
- `25` Saham IDX
- `Real-time` Data
- `AI-Powered` Analysis
- `Telegram` Bot

---

### 3. MARKET OVERVIEW CARDS

Ambil data dari `/api/market-summary`. Response API:
```json
{
  "total_stocks": 25,
  "advancing": 12,
  "declining": 8,
  "unchanged": 5,
  "avg_change": 0.32,
  "total_volume": 12500000000,
  "fear_greed": {
    "index": 62,
    "label": "Greed"
  }
}
```

Tampilkan sebagai 6 kartu kecil:
```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Fear     │ │Advancing │ │Declining │ │Unchanged │ │Avg Change│ │Volume    │
│ & Greed  │ │          │ │          │ │          │ │          │ │          │
│ 62/Greed │ │ 12       │ │ 8        │ │ 5        │ │ +0.32%   │ │ 12.5B    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Fear & Greed color coding:
- Extreme Greed (≥75): Merah
- Greed (55-74): Kuning
- Neutral (45-54): Abu-abu
- Fear (25-44): Biru
- Extreme Fear (<25): Hijau

Advancing = hijau, Declining = merah

---

### 4. TOP MOVERS — 3 Kolom

Ambil data dari 3 endpoint paralel:
- `/api/top-gainers?limit=5`
- `/api/top-losers?limit=5`
- `/api/top-volume?limit=5`

Response masing-masing:
```json
{
  "gainers": [
    {"code": "BBCA", "name": "Bank Central Asia", "change_pct": 3.45, "price": 10250},
    ...
  ]
}
```

Tampilkan 3 kartu bersampingan:

```
┌── TOP GAINERS ──┐ ┌── TOP LOSERS ───┐ ┌── TOP VOLUME ──┐
│ BBCA  +3.45%   │ │ TLKM  -2.10%   │ │ BBRI  25.5M    │
│ BMRI  +2.10%   │ │ ASII  -1.85%   │ │ BBCA  18.2M    │
│ ADRO  +1.75%   │ │ UNVR  -1.20%   │ │ BMRI  15.8M    │
│ TLKM  +1.50%   │ │ KLBF  -0.95%   │ │ ADRO  12.4M    │
│ ASII  +1.20%   │ │ CPIN  -0.75%   │ │ BBNI  10.1M    │
└────────────────┘ └────────────────┘ └────────────────┘
```

Gunakan warna:
- Gainers: hijau
- Losers: merah
- Volume: biru/putih

---

### 5. AI PERFORMANCE METRICS

Ambil data dari `/api/learning/performance`:
```json
{
  "accuracy_7day": 72.5,
  "accuracy_30day": 68.3,
  "overall_accuracy": 65.8,
  "winrate": 62.1,
  "avg_profit": 3.24,
  "total_predictions": 150,
  "model_type": "random_forest"
}
```

Tampilkan 4 metric card:
```
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Accuracy   │ │ Winrate    │ │ Avg Profit │ │ Total      │
│ 7-day      │ │            │ │            │ │ Predictions│
│ 72.5%      │ │ 62.1%      │ │ +3.24%     │ │ 150        │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

Color: >= 70% = hijau, 50-70% = kuning, < 50% = merah.

---

### 6. SECTOR PERFORMANCE

Ambil data dari `/api/sector-performance`:
```json
{
  "sectors": [
    {"name": "Banking", "change": 2.34, "flow": "INFLOW"},
    {"name": "Energy", "change": -1.12, "flow": "OUTFLOW"},
    ...
  ]
}
```

Tampilkan sebagai horizontal list dengan badge:

```
Banking      +2.34%  🟢 INFLOW
Energy       -1.12%  🔴 OUTFLOW
Consumer     +0.85%  🟢 INFLOW
Coal         -0.45%  ⚪ NEUTRAL
Property     +1.20%  🟢 INFLOW
Technology   -0.30%  ⚪ NEUTRAL
Healthcare   +0.15%  ⚪ NEUTRAL
```

Atau pakai progress bar horizontal lebih bagus.

---

### 7. RECENT PREDICTIONS TABLE

Ambil data dari `/api/learning/predictions?limit=5`:
```json
{
  "predictions": [
    {
      "stock_code": "BBCA",
      "recommendation": "BUY",
      "confidence": 85,
      "actual_result": "SUCCESS",
      "profit_pct": 2.34,
      "created_at": "2026-06-04"
    },
    ...
  ]
}
```

Tampilkan tabel:
```
┌───────┬──────────────┬────────┬────────┬────────┬────────────┐
│ Kode  │ Rekomendasi  │ Conf   │ Result │ Profit │ Tanggal    │
├───────┼──────────────┼────────┼────────┼────────┼────────────┤
│ BBCA  │ 🟢 BUY      │ 85%    │ ✅     │ +2.34% │ 2026-06-04 │
│ BBRI  │ 🟡 HOLD     │ 60%    │ ⏳     │ -      │ 2026-06-04 │
│ BMRI  │ 🔴 SELL     │ 72%    │ ✅     │ +1.5%  │ 2026-06-03 │
│ TLKM  │ 🟢 BUY      │ 68%    │ ❌     │ -1.2%  │ 2026-06-03 │
│ ADRO  │ 🟢 BUY      │ 91%    │ ✅     │ +4.1%  │ 2026-06-02 │
└───────┴──────────────┴────────┴────────┴────────┴────────────┘
```

---

### 8. FITUR-FITUR GRID

Buat grid 3-4 kolom card yang menjelaskan fitur:

| Icon | Nama Fitur | Deskripsi |
|------|-----------|-----------|
| 📊 | Real-time Stock Analysis | Data real-time dari Yahoo Finance untuk 25 saham IDX |
| 🤖 | AI Recommendations | Rekomendasi BUY/HOLD/SELL dengan confidence score |
| 📈 | Interactive Charts | Chart harga, RSI, MACD, Volume interaktif |
| 📱 | Telegram Bot | Analisis saham langsung dari Telegram |
| 🧠 | Machine Learning | Random Forest, XGBoost, LightGBM untuk prediksi |
| ⚙️ | AI Settings | Konfigurasi risk level, strategy, bobot indikator |
| 📋 | Excel Upload | Upload data harian untuk day trading analysis |
| 📊 | Performance Tracking | Track akurasi, winrate, dan profit prediksi |

Masing-masing card bisa diklik → navigasi ke halaman terkait.

---

### 9. STOCK LIST GRID

Ambil data dari `/api/stocks`. Response:
```json
{
  "stocks": [
    {"code": "BBCA", "name": "Bank Central Asia Tbk."},
    ...
  ]
}
```

Lalu untuk setiap stock, fetch perubahan harga dari `/api/stock/{code}?period=5d`.

Tampilkan sebagai grid atau list yang bisa difilter:

```
[Search: ______________]

BBCA   +1.23%  🟢   BMRI   -0.50%  🔴   BBRI   +0.75%  🟢
BBNI   +2.10%  🟢   TLKM   -1.30%  🔴   ASII   +0.20%  🟢
...
```

Setiap item bisa diklik → scroll/buka ke halaman detail analisis atau link ke halaman terpisah.

> **Catatan:** Untuk MVP, bisa pakai layout yang sama dengan sidebar di dashboard lama. Atau bikin grid view di halaman utama.

---

### 10. FOOTER

```html
<footer class="text-center text-muted py-3 border-top mt-4">
  <small>
    AI Stock Analyzer Indonesia v1.0.0 |
    Data: Yahoo Finance |
    <span class="text-warning">⚠️ DYOR — Do Your Own Research</span>
  </small>
</footer>
```

---

## Integrasi Data (JavaScript)

Buat fungsi-fungsi fetch paralel untuk ngambil data sekaligus:

```javascript
async function loadDashboard() {
    const [market, gainers, losers, volume, performance, sectors, predictions] = await Promise.all([
        fetch('/api/market-summary').then(r => r.json()),
        fetch('/api/top-gainers?limit=5').then(r => r.json()),
        fetch('/api/top-losers?limit=5').then(r => r.json()),
        fetch('/api/top-volume?limit=5').then(r => r.json()),
        fetch('/api/learning/performance').then(r => r.json()),
        fetch('/api/sector-performance').then(r => r.json()),
        fetch('/api/learning/predictions?limit=5').then(r => r.json()),
    ]);

    renderMarketOverview(market);
    renderTopGainers(gainers.gainers);
    renderTopLosers(losers.losers);
    renderTopVolume(volume.volume);
    renderPerformance(performance);
    renderSectors(sectors.sectors);
    renderPredictions(predictions.predictions);
}
```

## Yang Perlu Dibuat / Diubah

| File | Action | Keterangan |
|------|--------|-----------|
| `app/templates/dashboard.html` | **TULIS ULANG** | Ganti total dengan dashboard baru |
| `app/static/style.css` | **TAMBAH** | Tambah CSS untuk section-section baru |
| `app/static/dashboard.js` | **TULIS ULANG** | Ganti dengan logic dashboard baru (atau buat file baru `landing.js`) |

**Untuk halaman `upload_analyzer.html`:** punya style sendiri (light theme, purple gradient). Idealnya diseragamkan dengan theme dark, tapi bisa dijadikan tugas terpisah. Minimal tambahin navbar navigasi di atasnya.

---

## Referensi Visual & API

### Warna Dark Theme yang Dipakai

```css
:root {
    --sidebar-bg: #1a1d23;
    --card-bg: #1e2128;
    --border-color: #2a2d35;
    --bg: #13151a;
    --text: #e0e0e0;
    --text-muted: #888;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #eab308;
    --blue: #0d6efd;
    --purple: #a855f7;
}
```

### Layout Responsive

- Desktop (>768px): sidebar + multi-column grid
- Mobile (<768px): single column, stacked cards

### Error Handling

- Setiap fetch harus ada try/catch
- Kalau error: tampilkan pesan "Data tidak tersedia" jangan halaman putih
- Kalau loading: tampilkan skeleton/spinner

---

## Contoh Dashboard yang Sudah Ada (Referensi)

Halaman `dashboard.html` yang **lama** fokus ke per-stock detail. Yang **baru** harus jadi landing page yang kasih gambaran **keseluruhan sistem**.

Halaman `ai_settings.html` dan `ai_performance.html` sudah punya sidebar navigasi dengan link ke Dashboard. Pastikan navigation link di dashboard baru nyambung ke halaman-halaman tersebut.

---

## Urutan Prioritas Pengerjaan

1. **Navbar** — Navigasi ke semua halaman
2. **Hero/Welcome** — Jelaskan apa itu website ini
3. **Market Overview** — Fear & Greed, Advancing/Declining
4. **Top Movers** — Gainers, Losers, Volume
5. **Stock List Grid** — 25 saham dengan harga & change
6. **Sector Performance** — Per sektor
7. **Fitur Grid** — Card fitur-fitur
8. **AI Performance** — Accuracy, winrate
9. **Recent Predictions** — Tabel prediksi
10. **Footer**

---

## Contoh Fetch + Render

```javascript
async function renderMarketOverview() {
    const container = document.getElementById('marketOverview');
    container.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';

    try {
        const res = await fetch('/api/market-summary');
        const data = await res.json();

        container.innerHTML = `
            <div class="row g-2">
                <div class="col-4 col-md-2">
                    <div class="metric-card">
                        <div class="metric-value ${getFearGreedColor(data.fear_greed.index)}">
                            ${data.fear_greed.index}
                        </div>
                        <div class="metric-label">Fear & Greed</div>
                        <small class="text-muted">${data.fear_greed.label}</small>
                    </div>
                </div>
                <div class="col-4 col-md-2">
                    <div class="metric-card">
                        <div class="metric-value text-success">${data.advancing}</div>
                        <div class="metric-label">Advancing</div>
                    </div>
                </div>
                ...
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<div class="text-danger">Gagal memuat data market</div>';
    }
}
```

---

## Catatan Penting

1. **Jangan ubah file backend** — Semua data sudah tersedia dari API yang ada
2. **Jangan tambah dependency** — Cukup Bootstrap + Chart.js (via CDN) + custom CSS
3. **Konsisten dengan halaman lain** — Pakai dark theme yang sama
4. **Mobile friendly** — Semua section harus responsive
5. **Loading state** — Setiap section tunjukkan spinner/loading saat fetch
6. **Error state** — Setiap section tunjukkan pesan error jika fetch gagal
7. **Data kosong** — Setiap section handle case data kosong dengan baik
8. **File dashboard.html saat ini fokus ke per-stock detail** — Jangan hapus fungsionalitas itu, tapi pindahkan ke tab/section terpisah atau bikin halaman detail baru

---

Selamat mengerjakan! 🚀
