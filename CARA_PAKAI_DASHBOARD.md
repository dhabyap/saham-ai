# Cara Pakai Dashboard

## 3 Theme Modes

| Theme | Deskripsi |
|-------|-----------|
| **Light (Neumorphism)** | Tampilan terang dengan efek neumorphism (soft shadow/emboss). Default. |
| **Dark** | Tampilan gelap dengan aksen ungu-cyan. Cocok untuk penggunaan malam. |
| **Classy** | Tampilan terang dengan font serif, border tipis, dan aksen emas. |

## Cara Switch Theme

Klik tombol tema di pojok kanan header dashboard:

```
[Light] [Dark] [Classy]
```

Tema akan tersimpan otomatis di localStorage — saat dibuka kembali, tema terakhir akan aktif.

## Dashboard Sections

| Section | Isi |
|---------|-----|
| **Market Summary** | 6 card: Fear & Greed Index, Advancing/Declining stocks, Avg Change, Total Volume, Market Status |
| **AI Performance** | 4 card: Accuracy 7d, Win Rate, Avg Profit, Total Predictions |
| **Top Movers** | Top Gainers (hijau), Top Losers (merah), Top Volume (ungu) |
| **BPJS Day Trading Signals** | Candidate stocks untuk day trading dengan confidence score |
| **Long Term Accumulation** | Candidate stocks untuk investasi jangka panjang |
| **Sector Rotation** | 6 sektor dengan bar chart + change % + flow (Inflow/Neutral/Outflow) |
| **Recent Predictions** | Table: Stock, Signal, Confidence, Result, Profit %, Date |

## Features

### Search
- Ketik di search bar untuk filter stocks
- Hasil filter muncul di dropdown
- Tekan `Escape` atau klik luar untuk tutup

### Tab Switching
- Sidebar nav: Dashboard, Day Trading, Long Term, Analysis, Settings
- Header tabs: Overview, AI Performance, Market Movers, Sectors, Predictions
- Sidebar otomatis tertutup di mobile saat tab dipilih

### Responsive
- Desktop: sidebar tetap, grid 6/4/3 kolom
- Tablet: grid 3/2/1 kolom, sidebar bisa disembunyikan
- Mobile: sidebar fullscreen, header title disembunyikan

## Technical Notes

- Dibangun dengan **Vue 3** (Composition API) via CDN
- Theme persistence via **localStorage**
- Data masih **mock** — bisa diganti dengan API call nanti
- Route: `GET /dashboard`
