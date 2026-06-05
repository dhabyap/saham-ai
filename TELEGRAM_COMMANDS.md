# Telegram Bot Commands

## Overview

Bot Telegram untuk AI Stock Analyzer Indonesia. Menyediakan analisa saham IDX, watchlist, market summary, BPJS day trade, long term accumulation, dan AI recommendations.

---

## Command Groups

### Group 1: Core (WAJIB WORK)

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message with command list | `/start` |
| `/help` | Help & all commands | `/help` |
| `/analyze {code}` | Full stock analysis + chart | `/analyze BBCA` |
| `/watchlist` | Show your watchlist | `/watchlist` |
| `/market` | IDX market summary | `/market` |

### Group 2: Analysis Strategy

| Command | Description | Example |
|---------|-------------|---------|
| `/rekomendasi` | AI recommendation for top BUY stocks | `/rekomendasi` |
| `/daytrade {code}` | BPJS Day Trade signal for a stock | `/daytrade BBCA` |
| `/bpjs` | All BPJS Day Trade candidates | `/bpjs` |
| `/daytradecandidates` | Alias for /bpjs | `/daytradecandidates` |
| `/longterm {code}` | Long term accumulation analysis | `/longterm BBCA` |
| `/longtermcandidates` | All long term candidates | `/longtermcandidates` |

### Group 3: Market Data

| Command | Description | Example |
|---------|-------------|---------|
| `/topgainer` | Top gainers today | `/topgainer` |
| `/toploser` | Top losers today | `/toploser` |
| `/topvolume` | Top volume today | `/topvolume` |
| `/sentiment` | Market sentiment analysis | `/sentiment` |

### Group 4: Watchlist Management

| Command | Description | Example |
|---------|-------------|---------|
| `/add {code}` | Add stock to watchlist | `/add BBCA` |
| `/remove {code}` | Remove stock from watchlist | `/remove BBCA` |

### Group 5: AI & Feedback

| Command | Description | Example |
|---------|-------------|---------|
| `/feedback {value} {code}` | Submit feedback (benar/salah/bullish/bearish) | `/feedback benar BBCA` |
| `/accuracy` | AI prediction accuracy scores | `/accuracy` |
| `/performance` | AI performance summary | `/performance` |
| `/strategy` | Active strategy modes | `/strategy` |

---

## Response Format

Semua command mengembalikan pesan dengan format konsisten:
- Emoji prefix sesuai konteks
- Markdown formatting
- Error handling dengan `❌` prefix

## Error Handling

Setiap command memiliki try/except dengan format:
```
❌ Error: /{command} tidak tersedia saat ini
```

## Threading

Command berat (analyze, rekomendasi, daytrade, longterm) menggunakan
`asyncio.get_event_loop().run_in_executor()` untuk menghindari blocking event loop.

## Available Stocks

BBCA, BBRI, BMRI, BBNI, TLKM, ASII, UNVR, HMSP, GGRM, INDF, ADRO, ITMG,
PTBA, CPIN, KLBF, ICBP, JSMR, PGAS, EXCL, TOWR, SMGR, INTP, SMMA, AKRA, MEDC
