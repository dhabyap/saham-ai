# Panduan Long Term Strategy (Creative Trader)

## Cara Pakai

### Via Telegram
```
/longterm BBCA — Analisis akumulasi BBCA
/longtermcandidates — Lihat semua kandidat long term
```

### Via API
```
GET /api/long-term/BBCA
GET /api/long-term/candidates
```

### Cron
Jam 16:10 WIB — scan otomatis, kirim alert Telegram.

## Interpretasi

| Fase | Arti | Action |
|------|------|--------|
| Active Accumulation | Akumulasi asing 5+ hari | Siap entry |
| Early Accumulation | Akumulasi awal (3+ hari) | Mulai pantau |
| Neutral | Tidak ada akumulasi signifikan | Skip |
| Early Distribution | Distribusi 3+ hari | Hindari |
| Heavy Distribution | Distribusi 5+ hari | Exit jika sudah punya |

## Entry Zone
- **BUY (Lumpsum)** — Harga di lower zone akumulasi
- **ACCUMULATE (DCA)** — Harga di mid zone, beli bertahap

## Tips
- Fokus di fase active_accumulation
- Pastikan supply terserap (harga sideways, volume naik)
- Cek multi-timeframe alignment
- TP: +6% (swing) / +15% (long term)
- SL: -3% dari lower zone
