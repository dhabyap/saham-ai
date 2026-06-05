1|# Panduan BPJS Day Trading (Beli Pagi Jual Sore)
2|
3|## Apa itu BPJS?
4|Strategi day trading intraday: entry pagi, exit sebelum sore. Target profit 1.5%, cut loss 0.7%.
5|
6|## Cara Pakai
7|
8|### Via Telegram Bot
9|```
10|/daytrade BBCA — Cek signal BPJS untuk BBCA
11|/bpjs — Lihat semua kandidat hari ini
12|```
13|
14|### Via API
15|```
16|GET /api/day-trade/BBCA
17|GET /api/day-trade/candidates
18|```
19|
20|### Cron Otomatis
21|Setiap hari jam 16:05 WIB, sistem otomatis scan semua saham.
22|Kalo ada kandidat ENTER, dikirim alert ke Telegram.
23|
24|## Interpretasi Signal
25|
26|| Signal | Arti | Action |
27||--------|------|--------|
28|| ENTER | Breakout opening range + volume spike + foreign buy | Siap entry |
29|| WAIT | Belum memenuhi syarat | Pantau terus |
30|| EXIT_TP | Target profit tercapai | Ambil profit |
31|| EXIT_CL | Cut loss tersentuh | Keluar |
32|| EXIT_TIME | Lewat jam 14:30 | Tutup posisi |
33|
34|## Aturan Entry
35|1. Harga breakout opening range (30 menit pertama)
36|2. Volume 15 menit pertama > 1.5x rata-rata
37|3. Foreign flow kemarin NET BUY
38|4. Gap tidak lebih dari 3%
39|5. IHSG tidak gap down > 1%
40|
41|## Aturan Exit
42|- TP: +1.5% dari entry → ambil profit
43|- CL: -0.7% dari entry → cut loss
44|- Waktu: 14:30 WIB → tutup posisi (walaupun belum TP/CL)
45|
46|## Tips
47|- Fokus di saham likuid: BBCA, BBRI, BMRI, BBNI, TLKM, ASII
48|- Jangan entry kalo gap up > 3% (risiko reversal tinggi)
49|- Jangan entry kalo asing net sell kemarin
50|- Gunakan /analyze dulu buat cek trend besar
51|