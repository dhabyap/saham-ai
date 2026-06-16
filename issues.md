# Issues: Skeleton Loading untuk Semua Komponen Dashboard

## 📋 Deskripsi

Saat ini banyak komponen dashboard menunjukkan angka **0** atau teks **"-"** atau **kosong** sebelum data selesai dimuat. Ini jelek. Semua harus diganti dengan **skeleton loading** (animasi shimmer seperti placeholder) agar tampilan lebih profesional.

---

## 🎯 Tujuan

1. **Semua** angka 0, "-", atau empty state yang muncul karena data belum dimuat harus diganti skeleton.
2. Buat CSS skeleton reusable — pakai class `.skeleton` dan `.skeleton-text` yang sudah ada/baru.
3. Skeleton muncul saat `loading` state `true`, hilang saat data siap.
4. Tidak boleh ada flash of zero (FOZ) — angka 0 jangan sampai terlihat.

---

## 🧱 CSS Skeleton — Tambahkan di `dashboard.css`

Cari /* === Skeleton loading === */ di dashboard.css, replace isinya dengan:

```css
/* === Skeleton loading === */
.skeleton {
  background: linear-gradient(90deg, var(--surface-2) 25%, var(--surface) 50%, var(--surface-2) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
  color: transparent !important;
  user-select: none;
  pointer-events: none;
}

.skeleton-text {
  display: inline-block;
  height: 16px;
  width: 80%;
  margin: 4px 0;
}

.skeleton-value {
  display: inline-block;
  height: 32px;
  width: 60%;
  margin: 4px 0;
  border-radius: 8px;
}

.skeleton-card {
  min-height: 110px;
  border-radius: var(--radius);
}

.skeleton-table-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 12px;
  padding: 12px 14px;
}

.skeleton-table-row > div {
  height: 14px;
  border-radius: 4px;
}

.skeleton-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
}

.skeleton-badge {
  display: inline-block;
  height: 20px;
  width: 56px;
  border-radius: 12px;
}

.skeleton-chart {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, var(--surface-2) 25%, var(--surface) 50%, var(--surface-2) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## 📝 Daftar Komponen yg Perlu Skeleton

### A. Overview Tab — Market Overview Cards (6 cards)

**File:** `dashboard_vue.html`

**Sekitar baris 30-40:**

Sekarang:
```html
<div class="card card-accent card-big">
  <div class="card-header"><span class="card-label">Fear & Greed Index</span></div>
  <div><span class="card-value" style="color:var(--warning)">{{ market.fgi.value }}</span>...</div>
  ...
</div>
```

Jadi:
Pakai `v-if="!mrLoading"`, tambahkan skeleton `v-else`.

> [!TIP]
> Bungkus 6 card market overview dgn `<template>` dan duplikat sebagai skeleton.
> Skeleton card punya class `skeleton skeleton-card`.

Contoh:
```html
<div v-if="mrLoading" class="grid-6">
  <div v-for="n in 6" :key="n" class="card skeleton skeleton-card">
    <div class="skeleton skeleton-text" style="width:50%"></div>
    <div class="skeleton skeleton-value" style="width:40%"></div>
  </div>
</div>
<div v-else class="grid-6">
  <!-- card asli -->
</div>
```

**Cari pola:** Ada DUPLIKASI market overview cards (baris ~30 dan ~120). Keduanya harus di-skeleton-kan.

---

### B. Top Gainers / Losers / Volume Cards (3 cards)

**Sekitar baris 50-85.**

Sekarang menampilkan `v-for="item in movers.gainers"` — waktu loading, movers.gainers = [].

**Fix:** Bungkus dalam `v-if="!mrLoading"` skeleton, `v-else` konten asli.

Skeleton:
```html
<div v-if="mrLoading" class="grid-3">
  <div v-for="n in 3" :key="n" class="card">
    <div class="skeleton skeleton-text" style="width:40%"></div>
    <div v-for="m in 5" :key="m" class="mover-item">
      <div class="skeleton skeleton-text" style="width:50%"></div>
      <div class="skeleton skeleton-text" style="width:20%"></div>
    </div>
  </div>
</div>
```

---

### C. IHSG Chart Card

**Sekitar baris 90:**

Canvas `id="ihsgChart"` — waktu loading kosong.

**Fix:** Bungkus dgn `v-if="!mrLoading"`, tambah skeleton variant:
```html
<div v-if="mrLoading" class="card p-4" style="height:400px">
  <div class="skeleton-chart"></div>
</div>
```

---

### D. Foreign Accumulation Top 10 Table

**Sekitar baris 100**, `v-if="foreignOverviewStocks.length"` — waktu loading masih 0.

**Fix:** Tambah skeleton table rows.

---

### E. Pahlawan Bursa Warning Table

**Sekitar baris 120**, `v-if="pahlawanBursaStocks.length"`.

**Fix:** Sama, tambah skeleton.

---

### F. BPJS Day Trading Signals

**Sekitar baris 180:**

Ada `v-if="bpjsSignals.length === 0"` nampilin teks "⏳ Memuat data sinyal BPJS...".

**Fix:** Ganti jadi skeleton cards:
```html
<div v-if="bpjsSignals.length === 0" class="candidate-row">
  <div v-for="n in 4" :key="n" class="candidate-card">
    <div class="skeleton skeleton-text" style="width:40%"></div>
    <div class="skeleton skeleton-text" style="width:60%"></div>
    <div class="skeleton skeleton-value" style="width:30%"></div>
  </div>
</div>
```

---

### G. Long Term Accumulation Signals

**Sekitar baris 210:**

Sama seperti BPJS, teks loading diganti skeleton.

---

### H. Sector Rotation

**Sekitar baris 230:**

`v-for="s in sectors"` — waktu loading sectors = [].

**Fix:** skeleton list items.

---

### I. Recent Predictions Table

**Sekitar baris 245:**

Table predictions — waktu loading kosong.

**Fix:** skeleton table rows:
```html
<div v-if="predictions.length === 0 && mrLoading" class="card card-table">
  <div v-for="n in 5" :key="n" style="padding:12px 14px;border-bottom:1px solid var(--border-color)">
    <div class="skeleton-table-row">
      <div></div><div></div><div></div><div></div>
    </div>
  </div>
</div>
```

---

### J. IHSG Chart Tab (Already Done ✅)

Sudah ada skeleton loading untuk tab IHSG chart:
```html
<div v-if="mrLoading" class="section">
  ...
  <div class="skeleton-chart"></div>
  ...
</div>
```

Ini **OK**, no change needed.

---

### K. AI Analysis Tab

**Sekitar baris 676:**

Sekarang:
```html
<div v-if="mrLoadingAnalysis">
  <div class="card" style="text-align:center;padding:40px;color:var(--muted)">⏳ Loading analysis...</div>
</div>
```

**Fix:** Ganti jadi skeleton.

---

### L. Backtest Tab

**Sekitar baris 710-720:**

Ada `v-if="mrBtLoading"` dan `v-if="mrBtError"`.

Loading masih teks:
```html
<div class="card" style="text-align:center;padding:40px;color:var(--muted)">⏳ Loading backtest...</div>
```

**Fix:** Ganti jadi skeleton cards:
```html
<div v-if="mrBtLoading" class="section">
  <div class="stats-row">
    <div v-for="n in 4" :key="n" class="card skeleton skeleton-card"></div>
  </div>
  <div class="grid-3-card">
    <div v-for="n in 3" :key="n" class="card skeleton" style="height:140px"></div>
  </div>
</div>
```

---

### M. Day Trading — Signals Tab

**Sekitar baris 790:**

Teks:
```html
⏳ Memuat data sinyal...
```

**Fix:** Ganti skeleton cards.

---

### N. Day Trading — Candidates Tab

Table kosong waktu loading.

**Fix:** skeleton table rows.

---

### O. Day Trading — History Tab

Table kosong.

**Fix:** skeleton table rows.

---

### P. Long Term — Accumulation Tab

**Sekitar baris 870:**

Teks:
```html
⏳ Memuat data akumulasi...
```

**Fix:** skeleton candidate cards.

---

### Q. Long Term — Portfolio Tab

**Sekitar baris 890:**

Teks:
```html
Belum ada posisi portfolio.
```

**⚠️ Hati-hati:** Teks ini muncul saat **benar-benar tidak ada portfolio** (bukan loading). Jangan di-skeleton-kan. Cek state loading dulu.

---

### R. Long Term — Watchlist Tab

**Sekitar baris 920:**

Teks:
```html
Belum ada saham di watchlist.
```

Sama, bedakan antara **loading** vs **empty**.

---

### S. Analysis — Search Tab

**Sekitar baris 960:**

`v-if="filteredAnalysis.length === 0"` — teks:
```html
No stocks found for "..."
```

Ini bisa terjadi karena **loading** atau **memang tidak ada hasil**. Kalau loading, skeleton. Kalau memang tidak ada, teks.

---

### T. Shareholders — Overview Stat Cards

4 stat cards (`sh-card`) — waktu loading angka 0.

**Fix:** skeleton cards.

---

### U. Shareholders — Top Holders Table

**Sekitar baris ~1400:**

`v-else` nampilin "⏳ Loading..." — ganti skeleton table rows.

---

## 🛠️ Cara Kerja

### Step 1: Pahami Struktur

File yg diedit:
- `app/templates/dashboard_vue.html` — template Vue
- `app/static/dashboard.css` — styling
- `app/static/dashboard.js` — logika Vue

Di `dashboard.js`, ada beberapa **state** untuk loading:
- `mrLoading` — loading market reports / overview
- `mrLoadingAnalysis` — loading AI analysis
- `mrBtLoading` — loading backtest
- `shStockLoading`, `shHolderLoading`, `shTopLoading` — loading shareholders
- Semua state ini `ref(false)` jadi `true` pas fetch.

### Step 2: Pattern — Yang Harus Diikuti

Untuk setiap komponen:

```html
<!-- Loading state — skeleton -->
<div v-if="loadingState" class="...">
  <!-- skeleton placeholder -->
</div>

<!-- Error state — pesan error -->
<div v-else-if="errorState" class="...">
  ⚠️ {{ errorMessage }}
</div>

<!-- Empty state — data kosong -->
<div v-else-if="data.length === 0" class="...">
  Teks data kosong
</div>

<!-- Data state — konten asli -->
<div v-else>
  <!-- isi data yg sudah ada -->
</div>
```

### Step 3: Perhatikan Ini!

1. **Jangan Hapus** `v-if` yg sudah ada untuk empty state. Hanya tambah skeleton di loading state.
2. **Gunakan class `.skeleton`** yg sudah didaftarkan di CSS.
3. **Atur lebar** skeleton-text dengan `style="width:XX%"` agar bervariasi.
4. **Skeleton tidak boleh beda tinggi** dari konten asli — samakan ukuran.
5. **Test** dengan kasih delay di network atau matikan backend biar loading keliatan.
6. **Jangan skeleton-kan** pesan error (⚠️) — error tetaplah error.

---

## 📌 Prioritas

| Priority | Komponen | Lokasi (kira-kira baris) |
|----------|----------|--------------------------|
| 🔴 P1 | Market Overview cards (2x) | ~30, ~120 |
| 🔴 P1 | Top Movers cards | ~50 |
| 🔴 P1 | BPJS Signals | ~180 |
| 🔴 P1 | Long Term Signals | ~210 |
| 🟡 P2 | IHSG Chart card | ~90 |
| 🟡 P2 | Foreign Accumulation table | ~100 |
| 🟡 P2 | Pahlawan Bursa table | ~120 |
| 🟡 P2 | Sector Rotation | ~230 |
| 🟡 P2 | Predictions table | ~245 |
| 🟡 P2 | AI Analysis tab | ~676 |
| 🟡 P2 | Backtest tab | ~710 |
| 🟢 P3 | Day Trading tabs | ~790, ~830, ~850 |
| 🟢 P3 | Long Term tabs | ~870, ~890, ~920 |
| 🟢 P3 | Analysis Search | ~960 |
| 🟢 P3 | Shareholders sections | ~1300-1500 |

---

## ✅ Contoh Lengkap (Copy-Paste Boleh)

### Market Overview — Sebelum:

```html
<div class="grid-6">
  <div class="card card-accent card-big">
    <div class="card-header"><span class="card-label">Fear & Greed Index</span></div>
    <div><span class="card-value" style="color:var(--warning)">{{ market.fgi.value }}</span><span class="card-sub"> {{ market.fgi.label }}</span></div>
    <div class="fgi-outer"><div class="fgi-fill" :style="{ width: market.fgi.value + '%', ... }"></div></div>
  </div>
  ...5 card lainnya...
</div>
```

### Market Overview — Sesudah:

```html
<template v-if="!mrLoading && !mrError">
  <div class="grid-6">
    <!-- 6 cards asli -->
  </div>
</template>
<template v-else-if="mrLoading">
  <div class="grid-6">
    <div v-for="n in 6" :key="n" class="card skeleton skeleton-card">
      <div class="skeleton skeleton-text" style="width:50%"></div>
      <div class="skeleton skeleton-value" style="width:40%"></div>
    </div>
  </div>
</template>
```

### Table Loading — Sebelum:

```html
<tbody>
  <tr v-for="s in foreignOverviewStocks" :key="s.stock">
    ...
  </tr>
</tbody>
```

### Table Loading — Sesudah:

```html
<tbody v-if="!mrLoading">
  <tr v-for="s in foreignOverviewStocks" :key="s.stock">...</tr>
</tbody>
<tbody v-else>
  <tr v-for="n in 5" :key="n">
    <td v-for="c in 4" :key="c">
      <div class="skeleton skeleton-text" style="width:80%"></div>
    </td>
  </tr>
</tbody>
```

---

## 🔍 Cara Test

1. Buka `http://localhost:5000` (atau port yg dipakai)
2. Buka DevTools (F12) → Network tab
3. Centang **"Disable cache"**
4. Di Network tab, cari request API → Klik kanan → **"Block Request URL"** untuk beberapa endpoint
5. Reload — skeleton harus keliatan
6. Unblock — data muncul normal

Atau lebih gampang: Slow down network:
- DevTools → Network → Online dropdown → **"Slow 3G"**

---

## ⚠️ Catatan Penting

1. **Jangan edit** file `dashboard.js` untuk urusan skeleton — hanya `dashboard.html` dan `dashboard.css`.
2. **Jangan pakai** `v-show` untuk skeleton — pakai `v-if` / `v-else-if` / `v-else`.
3. Untuk `v-if` yg sudah ada, cek apakah loading state-nya terdefinisi. Kalau belum, perlu tambah ref baru di `dashboard.js`. Tapi usahakan pakai yg sudah ada: `mrLoading`, `mrLoadingAnalysis`, `mrBtLoading`, `shStockLoading`, `shHolderLoading`, `shTopLoading`.
4. Kalau ada komponen yg loading state-nya belum ada, tanya senior.
5. **Satu PR untuk semua perubahan** — jangan dipecah.
6. Commit message: `feat: add skeleton loading to all dashboard components`
