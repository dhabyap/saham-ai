## Issue 9 — Frontend: Visualisasi Bubble Chart Pemegang Saham

**Tujuan:**
Mengganti atau menambah visualisasi pemegang saham menjadi **Bubble Chart** yang lebih intuitif untuk melihat distribusi kepemilikan. Setiap bubble mewakili satu pemegang saham, dengan ukuran bubble berdasarkan besaran persentase kepemilikan.

**Kriteria:**
1. **Bubble Chart Overview:**
   - Gunakan `Chart.js` (plugin `chartjs-chart-bubble` atau custom `scatter` dengan `radius`).
   - Setiap bubble = 1 pemegang saham.
   - Ukuran bubble = % Kepemilikan.
   - Warna bubble = Berdasarkan kategori (Merah >=5%, Ungu <5%).
2. **Interaktivitas:**
   - **Click Bubble:** Saat di-klik, munculkan overlay atau panel samping (sidebar) yang menampilkan:
     - Daftar lengkap saham yang dimiliki pemegang saham tersebut.
     - Persentase kepemilikan per saham.
     - Total nilai/jumlah saham (jika tersedia).
3. **Pemisahan Kode:**
   - Tambahkan fungsi baru `renderShareholderBubbleChart()` di `charts.js`.
   - Pastikan tidak mengganggu chart yang sudah ada (Doughnut, Bar).
   - Gunakan state baru `shBubbleData` dan `shHolderSelected` di `state.js`.
4. **Isolasi:**
   - Fokus hanya pada file: `app/templates/views/shareholders.html`, `app/static/js/loaders.js`, `app/static/js/charts.js`, `app/static/js/state.js`.
   - **WAJIB:** Jangan ubah kode dashboard atau modul lain (Market Reports, Day Trading, dll).

**Verifikasi:**
1. Chart bubble muncul di tab Overview atau tab baru "Visualisasi".
2. Klik bubble → panel detail terbuka dengan list saham yang dimiliki.
3. Tidak ada error pada chart existing.
