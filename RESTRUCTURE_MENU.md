# 📋 Restructure Menu — Market Reports Only

## Kondisi Saat Ini

### Sidebar Navigation (6 menu)
| # | View | Label | Status |
|---|------|-------|--------|
| 1 | `dashboard` | Dashboard | ❌ HAPUS |
| 2 | `daytrading` | Day Trading | ❌ HAPUS |
| 3 | `longterm` | Long Term | ❌ HAPUS |
| 4 | `analysis` | Analysis | ❌ HAPUS |
| 5 | `settings` | Settings | ❌ HAPUS |
| 6 | `marketreports` | Market Reports | ✅ PERTAHANKAN |

### Market Reports Tabs (5 sub-tab)
| # | Tab ID | Label | Status |
|---|--------|-------|--------|
| 1 | `overview` | 📈 IHSG Chart | ✅ |
| 2 | `reports` | 📋 Reports | ✅ |
| 3 | `stocks` | 🏛️ Stock Tracker | ✅ |
| 4 | `analysis` | 🤖 AI Analysis | ✅ |
| 5 | `backtest` | 📊 Backtest | ✅ |

---

## Rencana Perubahan

### 1. Sidebar — Hapus Semua Menu Kecuali Market Reports

**Sebelum:**
```
┌──────────────────────┐
│  🟣 AI Stock Analyzer │
│                       │
│  ☰ Dashboard          │
│  ↔ Day Trading        │
│  ◆ Long Term          │
│  ≡ Analysis           │
│  ⚙ Settings           │
│  📊 Market Reports    │  ← active
│                       │
│  ─── Watchlist ───    │
│  BBCA  +1.2%          │
│  ...                  │
└──────────────────────┘
```

**Sesudah:**
```
┌──────────────────────┐
│  🟣 AI Stock Analyzer │
│                       │
│  📊 Market Reports    │  ← satu-satunya menu
│                       │
│  ─── Watchlist ───    │
│  BBCA  +1.2%          │
│  ...                  │
└──────────────────────┘
```

### 2. Default View — Langsung ke Market Reports

- Saat app load, langsung masuk ke `marketreports` view (bukan `dashboard`)
- Default tab: `overview` (IHSG Chart)
- URL hash default: `#marketreports/overview`

### 3. Header — Simplifikasi

- **Hamburger button:** Pertahankan (toggle sidebar open/close di mobile)
- **Header title:** Selalu tampilkan "Market Reports"
- **Search bar:** Pertahankan (useful untuk search saham)
- **Theme switcher:** Pertahankan
- **User info:** Pertahankan

### 4. Market Reports Tabs — Pertahankan Semua 5 Tab

Tidak ada perubahan di sub-tab Market Reports:

```
┌──────────────────────────────────────────────────────────────┐
│  📈 IHSG Chart │ 📋 Reports │ 🏛️ Stock Tracker │ 🤖 AI Analysis │ 📊 Backtest │
└──────────────────────────────────────────────────────────────┘
```

### 5. Watchlist di Sidebar — Pertahankan

Watchlist tetap ada di bawah sidebar karena berguna untuk quick view.

---

## File yang Perlu Diubah

### File: `app/templates/dashboard_vue.html`

| Bagian | Perubahan |
|--------|-----------|
| Tab buttons `dashboard`, `daytrading`, `longterm`, `analysis`, `settings` | ❌ Hapus semua tab button sections (baris ~52-74) |
| Tab buttons `marketreports` | ✅ Pertahankan, pindahkan ke posisi pertama (langsung tampil tanpa `v-else-if`) |
| Content `dashboard` view | ❌ Hapus semua content dashboard (tab-pane overview, aiperf, movers, sectors, preds) |
| Content `daytrading` view | ❌ Hapus semua content daytrading |
| Content `longterm` view | ❌ Hapus semua content longterm |
| Content `analysis` view | ❌ Hapus semua content analysis |
| Content `settings` view | ❌ Hapus semua content settings |
| Content `marketreports` view | ✅ Pertahankan semua |

### File: `app/static/dashboard.js`

| Bagian | Perubahan |
|--------|-----------|
| `navItems` array | ✅ Kurangi jadi 1 item: `{ view: 'marketreports', icon: '📊', label: 'Market Reports' }` |
| `switchView()` function | ✅ Simplifikasi — selalu ke marketreports |
| `firstTabs` map | ✅ Hapus semua kecuali `marketreports: 'overview'` |
| `headerTitle` computed | ✅ Selalu return "Market Reports" |
| URL routing (`syncViewFromUrl`, `navigateFromHash`) | ✅ Simplifikasi — marketreports saja |
| Dashboard data loading | ❌ Hapus load calls untuk dashboard, daytrading, longterm, analysis, settings |
| `switchMrTab()` | ✅ Pertahankan (tetap diperlukan untuk lazy load) |
| `setMrFilter()` | ✅ Pertahankan |

### File: `app/static/dashboard.css`

| Bagian | Perubahan |
|--------|-----------|
| Sidebar width | ✅ Bisa kecilkan (hanya 1 menu) atau pertahankan |
| Tab styles | ✅ Pertahankan |
| `.view-all` button styles (yang link ke daytrading/longterm) | ❌ Bisa hapus atau pertahankan |

### File: `app/api/routes.py`

| Bagian | Perubahan |
|--------|-----------|
| Routes untuk dashboard, daytrading, longterm, analysis, settings | ⚠️ Optional: bisa dihapus nanti, tapi tidak urgent |

---

## Diagram Alur App Baru

```
App Load
  │
  ▼
marketreports view (default)
  │
  ├── 📈 IHSG Chart (default tab)
  │     └── Chart IHSG + Market Summary
  │
  ├── 📋 Reports
  │     └── Market Reports list (Sesi 1 / Akhir Sesi)
  │
  ├── 🏛️ Stock Tracker
  │     └── Individual stock tracking
  │
  ├── 🤖 AI Analysis
  │     └── AI-powered market analysis
  │
  └── 📊 Backtest
        └── Strategy backtesting results
```

---

## Estimasi Dampak

| Aspek | Dampak |
|-------|--------|
| HTML size | 🔽 Berkurang ~60-70% (hapus 5 view content) |
| JS size | 🔽 Berkurang ~40-50% (hapus nav/routing complexity) |
| Load time | 🔼 Lebih cepat (lebih sedikit data dimuat) |
| UX | 🔼 Lebih fokus, tidak bingung pilih menu |
| Maintenance | 🔼 Lebih mudah, lebih sedikit code path |

---

## Status

- [ ] Buat rencana ini (✅ SELESAI)
- [ ] Edit `dashboard_vue.html` — hapus menu & content selain Market Reports
- [ ] Edit `dashboard.js` — simplifikasi navItems, routing, switchView
- [ ] Edit `dashboard.css` — optional cleanup
- [ ] Testing — pastikan semua 5 tab Market Reports berfungsi
- [ ] Cleanup optional routes di `routes.py`
