# Panduan BPJS Day Trading (Beli Pagi Jual Sore)

## Apa itu BPJS?
Strategi day trading intraday: entry pagi, exit sebelum sore. Target profit 1.5%, cut loss 0.7%.

## Cara Pakai

### Via Telegram Bot
```
/daytrade BBCA — Cek signal BPJS untuk BBCA
/daytrade-candidates — Lihat semua kandidat hari ini
```

### Via API
```
GET /api/day-trade/BBCA
GET /api/day-trade/candidates
```

### Cron Otomatis
Setiap hari jam 16:05 WIB, sistem otomatis scan semua saham.
Kalo ada kandidat ENTER, dikirim alert ke Telegram.

## Interpretasi Signal

| Signal | Arti | Action |
|--------|------|--------|
| ENTER | Breakout opening range + volume spike + foreign buy | Siap entry |
| WAIT | Belum memenuhi syarat | Pantau terus |
| EXIT_TP | Target profit tercapai | Ambil profit |
| EXIT_CL | Cut loss tersentuh | Keluar |
| EXIT_TIME | Lewat jam 14:30 | Tutup posisi |

## Aturan Entry
1. Harga breakout opening range (30 menit pertama)
2. Volume 15 menit pertama > 1.5x rata-rata
3. Foreign flow kemarin NET BUY
4. Gap tidak lebih dari 3%
5. IHSG tidak gap down > 1%

## Aturan Exit
- TP: +1.5% dari entry → ambil profit
- CL: -0.7% dari entry → cut loss
- Waktu: 14:30 WIB → tutup posisi (walaupun belum TP/CL)

## Tips
- Fokus di saham likuid: BBCA, BBRI, BMRI, BBNI, TLKM, ASII
- Jangan entry kalo gap up > 3% (risiko reversal tinggi)
- Jangan entry kalo asing net sell kemarin
- Gunakan /analyze dulu buat cek trend besar
