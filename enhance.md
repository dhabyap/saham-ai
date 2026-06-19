# Enhance: Halaman Shareholders — Visual & Informatif

## Latar Belakang

Halaman shareholders saat ini kurang informatif — cuma 3 angka statistik + tabel Top Holders. Padahal banyak data tersedia (7247 records, 955 emiten, 5183 pemegang saham, periode FEB2026).

**Tujuan:** Bikin halaman gampang dipahami orang awam. Pake chart visual, filter, tab navigasi jelas, insight naratif.

**Data existing:**
- DB `stock.db` → table `shareholders`
- Field: `stock_code`, `shareholder_name`, `share_count`, `share_percent`, `category`, `data_period`, `source`
- Dominant holder: UOB KAY HIAN PRIVATE LIMITED

---

## Cara Pengerjaan

Kerjakan **berurutan** — setiap issue adalah 1 commit/PR terpisah. Jangan skip.
Uji di browser sebelum lanjut issue berikutnya.

1. Backend: API endpoints baru
2. Frontend: Canvas + render chart di Overview
3. Frontend: Period selector
4. Frontend: Tab "Per Emiten" (search + detail)
5. Frontend: Tab "Top Holders" enhancement
6. Frontend: Overview enhancement (insight naratif)
7. Frontend: Educational tooltips
8. Frontend: Loading states per tab

---

## Issue 1 — Backend: API Endpoints Baru

**File:** `app/api/routes.py`

**Masalah:** Data yang available banyak (7247 records) tapi API belum sediain aggregasi buat chart.

**Criteria:**
- 4 endpoint baru di `routes.py`
- Masing-masing return JSON `{"status": "ok", ...}`
- Pakai `get_db()` pattern existing
- Jangan ubah endpoint existing — cuma tambah baru

### 1a. `GET /api/shareholders/distribution?period=FEB2026`

Distribusi kategori kepemilikan buat chart donut.

```python
@router.get("/shareholders/distribution")
def shareholder_distribution(period: Optional[str] = None):
    """Distribution of holdings by category."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            cur = conn.execute("""
                SELECT
                    SUM(CASE WHEN share_percent >= 5 THEN 1 ELSE 0 END) as large,
                    SUM(CASE WHEN share_percent >= 1 AND share_percent < 5 THEN 1 ELSE 0 END) as medium,
                    SUM(CASE WHEN share_percent >= 0.5 AND share_percent < 1 THEN 1 ELSE 0 END) as small,
                    SUM(CASE WHEN share_percent < 0.5 THEN 1 ELSE 0 END) as tiny,
                    COUNT(*) as total
                FROM shareholders
                WHERE data_period = ?
            """, (period,))
            row = dict(cur.fetchone())
        return {
            "status": "ok",
            "period": period,
            "distribution": row,
            "labels": {
                "large": "≥5% (Pengendali)",
                "medium": "1-5% (Signifikan)",
                "small": "0.5-1% (Minoritas)",
                "tiny": "<0.5% (Pemodal Kecil)"
            }
        }
    except Exception as e:
        logger.error("distribution error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
```

Return:
```json
{
  "status": "ok", "period": "FEB2026",
  "distribution": { "large": 123, "medium": 456, "small": 789, "tiny": 111, "total": 7247 },
  "labels": { "large": "≥5% (Pengendali)", ... }
}
```

### 1b. `GET /api/shareholders/top-stocks?period=FEB2026&limit=10`

10 emiten dgn jumlah pemegang saham terbanyak.

```python
@router.get("/shareholders/top-stocks")
def shareholder_top_stocks(period: Optional[str] = None, limit: int = Query(10, ge=1, le=50)):
    """Stocks with most shareholders."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            rows = conn.execute("""
                SELECT stock_code, COUNT(*) as holder_count,
                       ROUND(SUM(share_percent), 2) as total_pct,
                       ROUND(AVG(share_percent), 2) as avg_pct
                FROM shareholders WHERE data_period = ?
                GROUP BY stock_code
                ORDER BY holder_count DESC
                LIMIT ?
            """, (period, limit))
            data = [dict(r) for r in rows]
        return {"status": "ok", "period": period, "data": data}
    except Exception as e:
        logger.error("top-stocks error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
```

### 1c. `GET /api/shareholders/stats/detail?period=FEB2026`

Richer stats — tambah insight terpakai buat naratif.

```python
@router.get("/shareholders/stats/detail")
def shareholder_stats_detail(period: Optional[str] = None):
    """Detailed aggregate stats for a period."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            # Total records, stocks, holders
            total = conn.execute("SELECT COUNT(*) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            stocks = conn.execute("SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]
            holders = conn.execute("SELECT COUNT(DISTINCT shareholder_name) FROM shareholders WHERE data_period=?", (period,)).fetchone()[0]

            # Top holder
            top = conn.execute("""
                SELECT shareholder_name, COUNT(*) as stock_count, ROUND(SUM(share_percent), 2) as total_pct
                FROM shareholders WHERE data_period=?
                GROUP BY shareholder_name ORDER BY total_pct DESC LIMIT 1
            """, (period,)).fetchone()

            # Most held stock
            mhs = conn.execute("""
                SELECT stock_code, COUNT(*) as cnt FROM shareholders
                WHERE data_period=? GROUP BY stock_code ORDER BY cnt DESC LIMIT 1
            """, (period,)).fetchone()

            # Averages
            avg_holders = round(stocks / holders, 1) if holders else 0
            avg_pct = conn.execute("""
                SELECT ROUND(AVG(share_percent), 2) FROM shareholders WHERE data_period=?
            """, (period,)).fetchone()[0] or 0

        return {
            "status": "ok", "period": period,
            "stats": {
                "total_records": total, "total_stocks": stocks, "total_holders": holders,
                "top_holder": top[0] if top else "-",
                "top_holder_stocks": top[1] if top else 0,
                "top_holder_pct": top[2] if top else 0,
                "most_held_stock": mhs[0] if mhs else "-",
                "most_held_count": mhs[1] if mhs else 0,
                "avg_holders_per_stock": avg_holders,
                "avg_pct_per_holder": avg_pct,
            }
        }
    except Exception as e:
        logger.error("stats/detail error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
```

### 1d. `GET /api/shareholders/concentration?period=FEB2026&threshold=5`

Emiten dgn kepemilikan dominan. Data buat bar chart "top 10 konsentrasi tertinggi".

```python
@router.get("/shareholders/concentration")
def shareholder_concentration(period: Optional[str] = None, threshold: float = Query(5.0, ge=0.1, le=100)):
    """Stock concentration — which stocks have dominant holders."""
    try:
        from app.services.shareholder_service import get_db
        with get_db() as conn:
            rows = conn.execute("""
                SELECT stock_code, ROUND(MAX(share_percent), 2) as top_holder_pct,
                       ROUND(SUM(share_percent), 2) as total_owned_pct,
                       COUNT(*) as holder_count
                FROM shareholders WHERE data_period=?
                GROUP BY stock_code
                HAVING top_holder_pct >= ?
                ORDER BY top_holder_pct DESC LIMIT 10
            """, (period, threshold))
            dominant = [dict(r) for r in rows]
            total_stocks = conn.execute(
                "SELECT COUNT(DISTINCT stock_code) FROM shareholders WHERE data_period=?", (period,)
            ).fetchone()[0]
        return {
            "status": "ok", "period": period,
            "dominant_stocks": dominant,
            "summary": {
                "total_dominant": len(dominant),
                "dominant_pct": round(len(dominant) / total_stocks * 100, 1) if total_stocks else 0
            }
        }
    except Exception as e:
        logger.error("concentration error: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
```

**Verifikasi:** `curl http://localhost:8001/api/shareholders/distribution?period=FEB2026` → return JSON.

---

## Issue 2 — Frontend: Chart Canvas + Render di Overview

**Files:** `app/templates/views/shareholders.html`, `app/static/js/state.js`, `app/static/js/loaders.js`, `app/static/js/charts.js`, `app/static/dashboard.css`

**Masalah:** Fungsi `renderShareholderCharts()` di charts.js udah ada tapi HTML template gapunya `<canvas>` — chart gak muncul. Juga belum ada 3 chart baru (distribusi donut, top stocks bar, top holders horizontal bar).

**Criteria:**
- Tambah canvas + wrapper di template Overview
- Tambah state baru di state.js
- Tambah loader `loadShareholdersEnhanced()` di loaders.js
- Tambah fungsi render 3 chart baru di charts.js
- Tambah CSS grid 2 kolom buat chart layout
- Jangan hapus chart existing (`shBarChart` + `shDoughnutChart`) — tambah di sampingnya

### 2a. State (state.js) — tambah var baru

Letakkan setelah baris `var shStockSearched = ref(false);` (sekitar baris 168):

```javascript
// ── Shareholders Enhanced ──
var shDistribution = ref(null);
var shTopStocks = ref([]);
var shConcentration = ref([]);
var shDetailStats = ref(null);
var shDistLoading = ref(false);
```

Tambahkan chart instance variables di bagian atas file atau di `charts.js`:

Di `charts.js`, setelah baris `var shDoughnutInstance = null;` (baris 7):
```javascript
var shDistChartInstance = null;
var shTopStockChartInstance = null;
var shTopHolderChartInstance = null;
```

### 2b. HTML Template (shareholders.html)

Di dalam tab Overview (`currentTab === 'overview'`), setelah card "Info Terkini" (sebelum penutup `</template>` di baris ~62), tambah:

```html
<!-- Chart row: 2 kolom -->
<div class="chart-row">
  <div class="card chart-card">
    <div class="card-title">Distribusi Kepemilikan</div>
    <div class="chart-wrap" style="height:260px">
      <canvas id="shDistChart"></canvas>
    </div>
  </div>
  <div class="card chart-card">
    <div class="card-title">Emiten dengan Holders Terbanyak</div>
    <div class="chart-wrap" style="height:260px">
      <canvas id="shTopStockChart"></canvas>
    </div>
  </div>
</div>
<div class="card chart-card full-width" style="margin-bottom:16px">
  <div class="card-title">Top 10 Pemegang Saham Terbesar</div>
  <div class="chart-wrap" style="height:300px">
    <canvas id="shTopHolderChart"></canvas>
  </div>
</div>
```

### 2c. Loader (loaders.js) — fungsi baru

Tambahkan setelah fungsi `loadShareholders()` (setelah baris ~319):

```javascript
async function loadShareholdersEnhanced() {
  shDistLoading.value = true;
  try {
    var period = shareholdersLatestPeriod.value;
    if (!period) { shDistLoading.value = false; return; }

    var results = await Promise.allSettled([
      fetch('/api/shareholders/distribution?period=' + period).then(function(r) { return r.json(); }),
      fetch('/api/shareholders/top-stocks?period=' + period + '&limit=10').then(function(r) { return r.json(); }),
      fetch('/api/shareholders/stats/detail?period=' + period).then(function(r) { return r.json(); }),
      fetch('/api/shareholders/concentration?period=' + period + '&threshold=5').then(function(r) { return r.json(); }),
    ]);

    if (results[0].status === 'fulfilled' && results[0].value && results[0].value.status === 'ok')
      shDistribution.value = results[0].value.distribution;

    if (results[1].status === 'fulfilled' && results[1].value && results[1].value.status === 'ok')
      shTopStocks.value = results[1].value.data || [];

    if (results[2].status === 'fulfilled' && results[2].value && results[2].value.status === 'ok')
      shDetailStats.value = results[2].value.stats;

    if (results[3].status === 'fulfilled' && results[3].value && results[3].value.status === 'ok')
      shConcentration.value = results[3].value.dominant_stocks || [];

    window.Vue.nextTick(function() { renderShareholderChartsEnhanced(); });
  } catch(e) {
    console.error('Enhanced shareholders load failed:', e);
  } finally {
    shDistLoading.value = false;
  }
}
```

Panggil di akhir `loadShareholders()` — setelah baris `tryChart();` (baris ~318):

```javascript
  // Load enhanced chart data after basic data succeeds
  if (shareholdersStats.value.total_records > 0 && shareholdersLatestPeriod.value) {
    loadShareholdersEnhanced();
  }
```

### 2d. Charts (charts.js) — 3 chart baru

Tambahkan setelah fungsi `renderShareholderCharts()` (setelah baris ~134):

```javascript
function renderShareholderChartsEnhanced() {
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
  var accent = '#7C3AED';
  var accentLight = 'rgba(124,58,237,0.6)';

  // 1. DONUT — Distribusi Kepemilikan
  var dist = shDistribution.value;
  if (dist && dist.total) {
    var ctx1 = document.getElementById('shDistChart');
    if (ctx1) {
      if (shDistChartInstance) { shDistChartInstance.destroy(); shDistChartInstance = null; }
      shDistChartInstance = new Chart(ctx1, {
        type: 'doughnut',
        data: {
          labels: ['≥5% (Pengendali)', '1-5% (Signifikan)', '0.5-1% (Minoritas)', '<0.5% (Pemodal Kecil)'],
          datasets: [{
            data: [dist.large, dist.medium, dist.small, dist.tiny],
            backgroundColor: ['#EF4444', '#F59E0B', '#3B82F6', '#8B5CF6'],
            borderWidth: 0,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '55%',
          plugins: {
            legend: { position: 'bottom', labels: { color: textColor, font: { size: 10 }, boxWidth: 12, padding: 10 } },
            tooltip: {
              callbacks: {
                label: function(ctx) {
                  var total = dist.total;
                  var pct = ((ctx.raw / total) * 100).toFixed(1);
                  return ctx.label + ': ' + ctx.raw + ' data (' + pct + '%)';
                }
              }
            }
          }
        }
      });
    }
  }

  // 2. BAR — Top 10 Emiten dengan Holders Terbanyak
  var topStocks = shTopStocks.value;
  if (topStocks && topStocks.length) {
    var ctx2 = document.getElementById('shTopStockChart');
    if (ctx2) {
      if (shTopStockChartInstance) { shTopStockChartInstance.destroy(); shTopStockChartInstance = null; }
      shTopStockChartInstance = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: topStocks.map(function(s) { return s.stock_code; }),
          datasets: [{
            label: 'Jumlah Holders',
            data: topStocks.map(function(s) { return s.holder_count; }),
            backgroundColor: accentLight,
            borderColor: accent,
            borderWidth: 1,
            borderRadius: 4,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor, stepSize: 1 } },
            x: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } }
          }
        }
      });
    }
  }

  // 3. HORIZONTAL BAR — Top 10 Pemegang Saham Terbesar
  var topHolders = topShareholders.value;
  if (topHolders && topHolders.length) {
    var top10 = topHolders.slice().sort(function(a,b) { return (b.total_pct||0) - (a.total_pct||0); }).slice(0, 10);
    var ctx3 = document.getElementById('shTopHolderChart');
    if (ctx3) {
      if (shTopHolderChartInstance) { shTopHolderChartInstance.destroy(); shTopHolderChartInstance = null; }
      shTopHolderChartInstance = new Chart(ctx3, {
        type: 'bar',
        data: {
          labels: top10.map(function(s) {
            var name = s.shareholder_name || '';
            return name.length > 30 ? name.substring(0,28)+'...' : name;
          }),
          datasets: [{
            label: 'Total Kepemilikan %',
            data: top10.map(function(s) { return parseFloat((s.total_pct||0).toFixed(2)); }),
            backgroundColor: top10.map(function(s) {
              return (s.stock_count||0) > 20 ? 'rgba(239,68,68,0.7)' : 'rgba(124,58,237,0.7)';
            }),
            borderColor: top10.map(function(s) {
              return (s.stock_count||0) > 20 ? '#EF4444' : '#7C3AED';
            }),
            borderWidth: 1, borderRadius: 4,
          }]
        },
        options: {
          indexAxis: 'y', responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                afterLabel: function(ctx) {
                  var item = top10[ctx.dataIndex];
                  return 'Saham dipegang: ' + (item.stock_count||0) + ' emiten';
                }
              }
            }
          },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
            y: { grid: { display: false }, ticks: { color: textColor, font: { size: 9 } } }
          }
        }
      });
    }
  }
}
```

### 2e. CSS (dashboard.css)

Tambahkan sebelum `/* === Stats Row === */`:

```css
/* === Shareholders Charts === */
.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
@media (max-width: 768px) {
  .chart-row { grid-template-columns: 1fr; }
}
.chart-card {
  padding: 20px;
}
.chart-card .card-title {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--muted);
  margin-bottom: 12px;
}
.chart-card.full-width {
  grid-column: 1 / -1;
}
```

**Verifikasi:**
1. Buka `http://localhost:8001/#shareholders/overview`
2. Donut chart distribusi muncul dengan 4 segmen
3. Bar chart "Emiten dengan Holders Terbanyak" muncul
4. Horizontal bar "Top 10 Pemegang Saham Terbesar" muncul
5. Tidak ada error JS di console

---

## Issue 3 — Frontend: Period Selector

**Files:** `app/templates/views/shareholders.html`, `app/static/js/loaders.js`

**Masalah:** Data shareholder punya period (JAN2026, FEB2026, dll). Backend bisa filter per period. Tapi UI selalu pake `latest`, user gak bisa ganti.

**Criteria:**
- Dropdown period selector di atas tab navigasi di shareholders page
- Pake `shareholdersPeriods` (udah di state)
- Saat ganti period, reload semua data shareholders (stats, holders, stocks, charts)
- Default ke latest period

### 3a. Template HTML

Di dalam `<template>`, sebelum `<div class="tabs">` (sekitar baris 2), tambah:

```html
<div class="section-head" style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
  <div class="section-title">Ringkasan Kepemilikan</div>
  <div class="period-selector" v-if="shareholdersPeriods.length">
    <label class="text-xs text-muted mr-1">Periode:</label>
    <select v-model="selectedPeriod" @change="onPeriodChange" class="period-select">
      <option v-for="p in shareholdersPeriods" :key="p" :value="p">{{ p }}</option>
    </select>
  </div>
</div>
```

### 3b. State (state.js) — tambah:

```javascript
var selectedPeriod = ref(''); // selected period for shareholders
```

### 3c. Loaders (loaders.js)

Tambahkan fungsi:

```javascript
async function loadShareholdersByPeriod(period) {
  if (!period) return;
  shareholdersLoading.value = true;
  shareholdersError.value = '';
  try {
    var data = await cachedFetch('/api/shareholders/stats?period=' + period, 3600000);
    if (data.status === 'ok') shareholdersStats.value = data;
    var topData = await cachedFetch('/api/shareholders/top?period=' + period, 3600000);
    if (topData.status === 'ok') topShareholders.value = topData.data || [];
    var stocksData = await cachedFetch('/api/shareholders/stocks?period=' + period, 3600000);
    if (stocksData.status === 'ok') shStockList.value = stocksData.data || [];
    var popData = await cachedFetch('/api/shareholders/top?period=' + period + '&min_pct=0.1&limit=30', 3600000);
    if (popData.status === 'ok') popularHolders.value = popData.data || [];
    // Reload enhanced charts
    loadShareholdersEnhanced();
  } catch(e) {
    console.error('Period change load failed:', e);
    shareholdersError.value = 'Gagal memuat data periode ' + period;
  } finally {
    shareholdersLoading.value = false;
  }
}

function onPeriodChange() {
  loadShareholdersByPeriod(selectedPeriod.value);
}
```

### 3d. Modifikasi `loadShareholders()` — set selectedPeriod default

Di dalam `loadShareholders()`, setelah `shareholdersLatestPeriod.value = data.latest || '';` (sekitar baris 285), tambah:

```javascript
      if (data.latest && !selectedPeriod.value) {
        selectedPeriod.value = data.latest;
      }
```

### 3e. CSS

```css
.period-selector {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}
.period-select {
  background: var(--card-bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
}
.mr-1 { margin-right: 4px; }
```

**Verifikasi:**
1. Dropdown period muncul di Overview
2. Pilih period lain → data stats/chart berubah
3. Gak ada error JS

---

## Issue 4 — Frontend: Tab "Per Emiten" (Cari + Detail)

**Files:** `app/templates/views/shareholders.html`, `app/static/js/loaders.js`, `app/static/js/charts.js`

**Masalah:** State `shStockQuery`, `shStockResult`, `shStockList`, `shStockSelected` udah ada. Tapi UI tab "By Stock" belum dibuat.

**Criteria:**
- Tab baru "Per Emiten" di samping "Overview" dan "Top Holders"
- Search box + chip grid dari `shStockList`
- Detail: 3 stat cards + bar chart + table
- Chart horizontal per holder buat stock terpilih

### 4a. Template — tambah tab button

Di `<div class="tabs">`, tambah button baru setelah "Top Holders":

```html
<button class="tab-btn" :class="{ active: currentTab === 'stocks' }"
        @click="currentTab = 'stocks'">Per Emiten</button>
```

### 4b. Template — tab pane "stocks"

Setelah tab-pane `top`, tambah:

```html
<div class="tab-pane" :class="{ active: currentTab === 'stocks' }">
  <div class="section">
    <div class="card p-4">
      <!-- Search -->
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <input type="text" v-model="shStockQuery"
               placeholder="Cari kode saham..."
               @keyup.enter="searchStockShareholders"
               style="flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:6px;
                      background:var(--card-bg);color:var(--text);font-size:13px" />
        <button class="btn btn-sm" @click="searchStockShareholders">Cari</button>
      </div>

      <!-- Stock chip grid -->
      <div v-if="shStockList.length && !shStockResult.length && !shStockLoading"
           style="display:flex;flex-wrap:wrap;gap:6px;max-height:180px;overflow-y:auto">
        <div v-for="s in shStockList.slice(0, 80)" :key="s.stock_code"
             @click="selectStockShareholder(s.stock_code)"
             style="cursor:pointer;padding:4px 10px;border-radius:12px;
                    background:var(--accent);color:#fff;font-size:12px;
                    white-space:nowrap">
          {{ s.stock_code }}
          <small style="opacity:0.7">({{ s.holder_count }})</small>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="shStockLoading" class="text-center text-muted" style="padding:20px">
        Mencari data...
      </div>

      <!-- Error -->
      <div v-if="shStockError" class="text-sm" style="color:var(--danger)">
        {{ shStockError }}
      </div>

      <!-- Result detail -->
      <div v-if="shStockResult.length && shStockActiveLabel">
        <div class="section-title" style="font-size:18px;margin:16px 0 12px;padding:0">
          {{ shStockActiveLabel }}
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px">
          <div class="card text-center p-3">
            <div class="font-bold text-accent" style="font-size:20px">{{ shStockResult.length }}</div>
            <div class="text-xs text-muted">Pemegang Saham</div>
          </div>
          <div class="card text-center p-3">
            <div class="font-bold text-success" style="font-size:20px">
              {{ totalSharePct(shStockResult).toFixed(1) }}%
            </div>
            <div class="text-xs text-muted">Total Kepemilikan</div>
          </div>
          <div class="card text-center p-3">
            <div class="font-bold text-warning" style="font-size:20px">
              {{ dominantHolderPct(shStockResult) }}
            </div>
            <div class="text-xs text-muted">Pengendali Teratas</div>
          </div>
        </div>

        <!-- Bar chart detail stock -->
        <div class="chart-wrap" style="height:200px;margin-bottom:16px">
          <canvas id="shStockDetailChart"></canvas>
        </div>

        <!-- Table -->
        <div class="card card-table">
          <table class="table-compact">
            <thead>
              <tr>
                <th>Pemegang Saham</th>
                <th>%</th>
                <th>Kepemilikan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in shStockResult" :key="s.shareholder_name">
                <td style="font-size:12px">{{ s.shareholder_name }}</td>
                <td :style="s.share_percent >= 5 ? 'color:var(--danger);font-weight:700' : ''">
                  {{ s.share_percent.toFixed(2) }}%
                </td>
                <td class="text-muted">{{ s.share_count || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Empty -->
      <div v-if="shStockSearched && !shStockResult.length && !shStockLoading && !shStockError"
           class="text-center text-muted" style="padding:20px">
        Data tidak ditemukan. Coba kode saham lain.
      </div>
    </div>
  </div>
</div>
```

### 4c. Helper functions + loader (app.js / loaders.js)

Tambahkan di `loaders.js`:

```javascript
function totalSharePct(rows) {
  return rows.reduce(function(sum, r) { return sum + (r.share_percent || 0); }, 0);
}
function dominantHolderPct(rows) {
  if (!rows.length) return '-';
  var top = rows.slice().sort(function(a,b) { return (b.share_percent||0) - (a.share_percent||0); })[0];
  return top.share_percent.toFixed(1) + '%';
}
async function searchStockShareholders() {
  var code = shStockQuery.value.trim().toUpperCase();
  if (!code) return;
  shStockLoading.value = true;
  shStockError.value = '';
  shStockSearched.value = true;
  try {
    var period = selectedPeriod.value || shareholdersLatestPeriod.value;
    var res = await fetch('/api/shareholders/' + code + '?period=' + period);
    var json = await res.json();
    if (json.status === 'ok' && json.data && json.data.length) {
      shStockResult.value = json.data;
      window.Vue.nextTick(function() { renderStockDetailChart(); });
    } else {
      shStockResult.value = [];
      shStockError.value = 'Data tidak ditemukan untuk ' + code;
    }
  } catch(e) {
    shStockError.value = 'Gagal memuat: ' + e.message;
    shStockResult.value = [];
  } finally {
    shStockLoading.value = false;
  }
}
function selectStockShareholder(code) {
  shStockQuery.value = code;
  searchStockShareholders();
}
```

### 4d. Chart detail stock (charts.js)

```javascript
var shStockDetailChartInstance = null;

function renderStockDetailChart() {
  var data = shStockResult.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';

  var sorted = data.slice().sort(function(a,b) { return (b.share_percent||0) - (a.share_percent||0); });
  var labels = sorted.map(function(s) {
    var n = s.shareholder_name || '';
    return n.length > 25 ? n.substring(0,23)+'...' : n;
  });
  var vals = sorted.map(function(s) { return parseFloat((s.share_percent||0).toFixed(2)); });

  var ctx = document.getElementById('shStockDetailChart');
  if (!ctx) return;
  if (shStockDetailChartInstance) { shStockDetailChartInstance.destroy(); shStockDetailChartInstance = null; }
  shStockDetailChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '% Kepemilikan',
        data: vals,
        backgroundColor: vals.map(function(v) { return v >= 5 ? 'rgba(239,68,68,0.7)' : 'rgba(124,58,237,0.6)'; }),
        borderColor: vals.map(function(v) { return v >= 5 ? '#EF4444' : '#7C3AED'; }),
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
        y: { grid: { display: false }, ticks: { color: textColor, font: { size: 9 } } }
      }
    }
  });
}
```

**Verifikasi:**
1. Tab "Per Emiten" muncul di sidebar/tabs
2. Klik salah satu chip saham → detail + chart muncul
3. Ketik "BBCA" di search → enter → data + chart render
4. Bar chart merah buat holder ≥5% (pengendali), ungu buat <5%

---

## Issue 5 — Frontend: Tab "Top Holders" Enhancement

**Files:** `app/templates/views/shareholders.html`, `app/static/js/loaders.js`, `app/static/js/charts.js`, `app/static/js/state.js`

**Masalah:** Tab Top Holders existing cuma tabel Nama + Total%. State `shHolderQuery`, `shHolderResult`, `shHolderLoading`, `popularHolders` udah ada tapi gak dipake.

**Criteria:**
- Search box + popular holders chips
- Horizontal bar chart (existing `shBarChart` — udah jalan)
- Klik holder → tampilkan portofolio detail (stock apa aja yg dipegang)
- Portfolio chart per holder

### 5a. Template — enhance tab `top`

Ganti isi tab-pane `top` jadi:

```html
<div class="tab-pane" :class="{ active: currentTab === 'top' }">
  <template v-if="shareholdersLoading">
    <div class="section"><div class="section-title">Memuat top holders...</div>
      <!-- skeleton -->
      <div class="card p-4" style="padding:0;overflow:hidden">
        <div v-for="n in 8" :key="n" class="skeleton-table-row" style="grid-template-columns:1fr 80px;margin-bottom:4px;padding:8px 12px"><div></div><div></div></div>
      </div>
    </div>
  </template>
  <template v-else-if="shareholdersError">
    <div class="section">
      <div class="card p-4" style="border-left:4px solid var(--danger);color:var(--danger)">
        <div class="font-semibold mb-2">Top holders gagal dimuat</div>
        <p class="text-sm">{{ shareholdersError }}</p>
      </div>
    </div>
  </template>
  <template v-else>
    <div class="section">
      <!-- Search holder -->
      <div class="card p-4" style="margin-bottom:16px">
        <div style="display:flex;gap:8px;margin-bottom:12px">
          <input type="text" v-model="shHolderQuery"
                 placeholder="Cari nama pemegang saham..."
                 @keyup.enter="searchShareholdersByHolder"
                 style="flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:6px;
                        background:var(--card-bg);color:var(--text);font-size:13px" />
          <button class="btn btn-sm" @click="searchShareholdersByHolder">Cari</button>
        </div>

        <!-- Popular holders chips -->
        <div v-if="popularHolders.length && !shHolderResult.length && !shHolderLoading">
          <div class="text-xs text-muted mb-1">Populer:</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            <div v-for="h in popularHolders.slice(0, 20)" :key="h.shareholder_name"
                 @click="selectHolder(h.shareholder_name)"
                 style="cursor:pointer;padding:3px 8px;border-radius:10px;
                        background:var(--accent);color:#fff;font-size:11px;
                        white-space:nowrap">
              {{ h.shareholder_name.length > 30 ? h.shareholder_name.substring(0,28)+'..' : h.shareholder_name }}
            </div>
          </div>
        </div>
      </div>

      <!-- Portfolio detail -->
      <div v-if="shHolderResult.length && shHolderActiveName">
        <div class="section-title" style="font-size:18px;margin:0 0 12px;padding:0">
          Portofolio: {{ shHolderActiveName }}
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px">
          <div class="card text-center p-3">
            <div class="font-bold text-accent" style="font-size:20px">{{ shHolderResult.length }}</div>
            <div class="text-xs text-muted">Saham Dipegang</div>
          </div>
          <div class="card text-center p-3">
            <div class="font-bold text-success" style="font-size:20px">
              {{ totalSharePct(shHolderResult).toFixed(1) }}%
            </div>
            <div class="text-xs text-muted">Total Portofolio</div>
          </div>
          <div class="card text-center p-3">
            <div class="font-bold text-warning" style="font-size:20px">
              {{ dominantHolderPct(shHolderResult) }}
            </div>
            <div class="text-xs text-muted">Holding Terbesar</div>
          </div>
        </div>

        <!-- Portfolio chart -->
        <div class="chart-wrap" style="height:200px;margin-bottom:16px">
          <canvas id="shHolderPortfolioChart"></canvas>
        </div>

        <!-- Table -->
        <div class="card card-table" style="margin-bottom:16px">
          <table class="table-compact">
            <thead>
              <tr>
                <th>Stock</th>
                <th>%</th>
                <th>Kepemilikan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in shHolderResult" :key="s.stock_code">
                <td><strong>{{ s.stock_code }}</strong></td>
                <td>{{ s.share_percent.toFixed(2) }}%</td>
                <td class="text-muted">{{ s.share_count || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Bar chart top holders (existing) -->
      <div v-if="topShareholders.length">
        <div class="section-title" style="font-size:16px;margin:0 0 12px;padding:0">
          Top Shareholders
        </div>
        <div class="chart-wrap" style="height:300px;margin-bottom:12px">
          <canvas id="shBarChart"></canvas>
        </div>
        <div class="card card-table">
          <table class="table-compact">
            <thead>
              <tr>
                <th>Name</th>
                <th>Jumlah Saham</th>
                <th>Total %</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in filteredTopShareholders" :key="s.shareholder_name"
                  @click="selectHolder(s.shareholder_name)"
                  style="cursor:pointer">
                <td>{{ s.shareholder_name }}</td>
                <td>
                  {{ s.stock_count || 0 }}
                  <span v-if="(s.stock_count||0) >= 30" class="badge-collector">Kolektor</span>
                </td>
                <td>{{ (s.total_pct || 0).toFixed(2) }}%</td>
              </tr>
            </tbody>
          </table>
          <div class="table-info" v-if="topShareholders.length">
            Menampilkan {{ topShareholders.length }} pemegang saham terbesar
          </div>
        </div>
      </div>
    </div>
  </template>
</div>
```

### 5b. Loaders — portofolio search

```javascript
async function searchShareholdersByHolder() {
  var name = shHolderQuery.value.trim().toUpperCase();
  if (!name) return;
  shHolderLoading.value = true;
  shHolderError.value = '';
  shHolderSearched.value = true;
  try {
    var period = selectedPeriod.value || shareholdersLatestPeriod.value;
    var res = await fetch('/api/shareholders/search/' + encodeURIComponent(name) + '?period=' + period);
    var json = await res.json();
    if (json.status === 'ok' && json.data && json.data.length) {
      shHolderResult.value = json.data;
      window.Vue.nextTick(function() { renderHolderPortfolioChart(); });
    } else {
      shHolderResult.value = [];
      shHolderError.value = 'Data tidak ditemukan untuk "' + name + '"';
    }
  } catch(e) {
    shHolderError.value = 'Gagal memuat: ' + e.message;
    shHolderResult.value = [];
  } finally {
    shHolderLoading.value = false;
  }
}

function selectHolder(name) {
  shHolderQuery.value = name;
  searchShareholdersByHolder();
}
```

**Catatan:** Fungsi `selectHolder()` di existing `loaders.js` fetch ke `/api/shareholders/holder/{name}` — endpoint itu TIDAK ADA. Ganti panggilannya ke `/api/shareholders/search/{name}` seperti di atas. Atau hapus fungsi lama, pake yang baru.

### 5c. Portfolio chart (charts.js)

```javascript
var shHolderPortfolioChartInstance = null;

function renderHolderPortfolioChart() {
  var data = shHolderResult.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';

  var sorted = data.slice().sort(function(a,b) { return (b.share_percent||0) - (a.share_percent||0); }).slice(0, 15);
  var labels = sorted.map(function(s) { return s.stock_code; });
  var vals = sorted.map(function(s) { return parseFloat((s.share_percent||0).toFixed(2)); });

  var ctx = document.getElementById('shHolderPortfolioChart');
  if (!ctx) return;
  if (shHolderPortfolioChartInstance) { shHolderPortfolioChartInstance.destroy(); shHolderPortfolioChartInstance = null; }
  shHolderPortfolioChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '% Kepemilikan',
        data: vals,
        backgroundColor: 'rgba(16,185,129,0.6)',
        borderColor: '#10B981',
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
        y: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } }
      }
    }
  });
}
```

### 5d. CSS

```css
.badge-collector {
  display:inline-block;padding:1px 6px;border-radius:8px;
  background:rgba(245,158,11,0.15);color:#F59E0B;
  font-size:10px;font-weight:600;margin-left:4px;
}
.table-info {
  padding:8px 12px;font-size:11px;color:var(--muted);
  border-top:1px solid var(--border);
}
```

**Verifikasi:**
1. Tab Top Holders — search box + chips muncul
2. Klik chip "UOB KAY HIAN" → portfolio detail + chart muncul
3. Bar chart existing `shBarChart` masih muncul
4. Table punya kolom "Jumlah Saham" + badge "Kolektor" kalau ≥30
5. Klik baris tabel → portfolio detail

---

## Issue 6 — Frontend: Overview Enhancement (Insight Naratif)

**Files:** `app/templates/views/shareholders.html`

**Masalah:** Overview cuma 3 angka + chart. Belum ada insight naratif yg bikin orang awam ngerti.

**Criteria:**
- Tambah section insight di bawah chart
- Pake data dari `shDetailStats`, `shDistribution`, `shTopStocks`
- Bahasa Indonesia, kalimat sederhana

### Template — setelah chart-row, tambah:

```html
<!-- Insight naratif -->
<div class="card p-4" v-if="shDetailStats" style="margin-bottom:16px">
  <div class="card-title" style="font-size:13px;font-weight:600;text-transform:uppercase;
       letter-spacing:0.5px;color:var(--muted);margin-bottom:12px">
    Ringkasan
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;line-height:1.6">
    <div>
      <span class="text-muted">📊 Total data:</span>
      <strong>{{ shDetailStats.total_records }}</strong> catatan kepemilikan
    </div>
    <div>
      <span class="text-muted">🏢 Emiten:</span>
      <strong>{{ shDetailStats.total_stocks }}</strong> perusahaan terpantau
    </div>
    <div>
      <span class="text-muted">👥 Pemegang saham:</span>
      <strong>{{ shDetailStats.total_holders }}</strong> nama unik
    </div>
    <div>
      <span class="text-muted">📈 Rata-rata:</span>
      <strong>{{ shDetailStats.avg_holders_per_stock }}</strong> pemegang per emiten
    </div>
    <div v-if="shDetailStats.top_holder !== '-'">
      <span class="text-muted">🥇 Pemegang dominan:</span>
      <strong>{{ shDetailStats.top_holder }}</strong>
      ({{ shDetailStats.top_holder_pct }}% di {{ shDetailStats.top_holder_stocks }} emiten)
    </div>
    <div v-if="shDetailStats.most_held_stock !== '-'">
      <span class="text-muted">⭐ Emiten terpopuler:</span>
      <strong>{{ shDetailStats.most_held_stock }}</strong>
      ({{ shDetailStats.most_held_count }} pemegang)
    </div>
  </div>
  <div v-if="shDistribution && shDistribution.total" style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border);font-size:12px;color:var(--muted)">
    Dari <strong>{{ shDistribution.total }}</strong> data kepemilikan:
    <span v-if="shDistribution.large"><strong>{{ shDistribution.large }}</strong> pengendali (≥5%), </span>
    <span v-if="shDistribution.medium"><strong>{{ shDistribution.medium }}</strong> signifikan (1-5%), </span>
    <span v-if="shDistribution.small"><strong>{{ shDistribution.small }}</strong> minoritas (0.5-1%), </span>
    <span v-if="shDistribution.tiny"><strong>{{ shDistribution.tiny }}</strong> pemodal kecil (&lt;0.5%).</span>
  </div>
</div>
```

**Verifikasi:**
1. Overview — insight box muncul di bawah chart
2. Angka sesuai data (cek total_records = 7247)
3. Gak ada error JS

---

## Issue 7 — Frontend: Educational Tooltips

**Files:** `app/templates/views/shareholders.html`

**Masalah:** Istilah "shareholder", "total_pct", "stock_count" — orang awam gak ngerti.

**Criteria:**
- Tambah helper text/tooltip pake icon ℹ️ di setiap section
- Bahasa Indonesia

### Template — tambah di beberapa tempat:

Di header tab Overview, setelah section-title:
```html
<div class="section-title">Ringkasan Kepemilikan
  <span class="help-tip" title="Menampilkan ringkasan seluruh data kepemilikan saham di atas 1% yang tercatat di Bursa Efek Indonesia">ℹ️</span>
</div>
```

Di card-title chart:
```html
<div class="card-title">
  Distribusi Kepemilikan
  <span class="help-tip" title="Mengelompokkan pemegang saham berdasarkan besaran kepemilikannya. ≥5% = pengendali (bisa punya pengaruh besar).">ℹ️</span>
</div>
```

Di kolom tabel:
```html
<th>Total %
  <span class="help-tip" title="Total persentase kepemilikan di seluruh saham yang dipegang">ℹ️</span>
</th>
```

CSS:
```css
.help-tip {
  display:inline-block;cursor:help;font-size:12px;color:var(--muted);
  margin-left:4px;vertical-align:middle;opacity:0.6;
}
.help-tip:hover { opacity:1; }
```

**Verifikasi:**
1. Icon ℹ️ muncul di section title, chart title, header tabel
2. Hover → tooltip muncul (native `title` attribute)
3. Tidak ada perubahan layout signifikan

---

## Issue 8 — Frontend: Loading States per Tab

**Files:** `app/templates/views/shareholders.html`

**Masalah:** Semua tab pake `shareholdersLoading` sama. Tab Per Emiten/Holders loading yang beda gak terlihat.

**Criteria:**
- Tab Overview: pake `shareholdersLoading` + `shDistLoading` (buat chart)
- Tab Per Emiten: pake `shStockLoading` (udah ada)
- Tab Top Holders: pake `shHolderLoading` + `shareholdersLoading`
- Skeleton pattern existing

### Template — skeleton untuk `shDistLoading` di Overview

Tambahkan di dalam tab-pane Overview, sebelum `<div v-if="!shareholdersLoading">`:
```html
<template v-if="shDistLoading && !shareholdersLoading">
  <div class="chart-row">
    <div v-for="n in 2" :key="n" class="card chart-card">
      <div class="skeleton-text" style="width:160px;height:12px;margin-bottom:12px"></div>
      <div class="skeleton-value" style="height:240px;border-radius:8px"></div>
    </div>
  </div>
  <div class="card chart-card full-width" style="margin-bottom:16px">
    <div class="skeleton-text" style="width:200px;height:12px;margin-bottom:12px"></div>
    <div class="skeleton-value" style="height:280px;border-radius:8px"></div>
  </div>
</template>
```

Untuk tab Per Emiten — skeleton sudah include di template Issue 4 (`shStockLoading`).

Untuk tab Top Holders — skeleton sudah include di template Issue 5 (`shHolderLoading`).

**Verifikasi:**
1. Overview: skeleton chart muncul sementara data enhanced loading
2. Per Emiten: skeleton pas search
3. Top Holders: skeleton pas search portfolio

---

## Daftar Perubahan Lengkap

Semua file yg diubah/ditambah:

| File | Tipe | Perubahan |
|------|------|-----------|
| `app/api/routes.py` | Backend | +4 endpoint: distribution, top-stocks, stats/detail, concentration |
| `app/templates/views/shareholders.html` | Frontend | Restruktur 3 tab: Overview (charts+insight), Per Emiten, Top Holders |
| `app/static/js/state.js` | Frontend | +7 var: shDistribution, shTopStocks, shConcentration, shDetailStats, shDistLoading, selectedPeriod |
| `app/static/js/loaders.js` | Frontend | +5 fungsi: loadShareholdersEnhanced, loadShareholdersByPeriod, onPeriodChange, searchStockShareholders, searchShareholdersByHolder |
| `app/static/js/charts.js` | Frontend | +5 chart: donut distribusi, bar top stocks, horizontal top holders, bar detail stock, bar portfolio holder |
| `app/static/dashboard.css` | Frontend | +.chart-row, .chart-card, .period-selector, .badge-collector, .help-tip, .table-info |
| `app/templates/dashboard_vue.html` | Frontend | Update `?v=` cache buster |

**⚠️ JANGAN UBAH file lain.** Fungsi existing (`loadShareholders`, `loadDashboardData`, `renderShareholderCharts`, dll) tetap jalan — hanya ditambah, bukan dihapus/diganti.
