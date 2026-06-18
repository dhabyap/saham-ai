# Issues

## Perbaikan Halaman Web (Bug & Loading Error)

Status: Open
Prioritas: High
Level pengerjaan: Junior Programmer

### Tujuan
Website mengalami banyak error dan bug setelah proses refactor. Beberapa menu tidak menampilkan data dan loading indicator tidak berjalan sebagaimana mestinya. Tujuan tugas ini adalah memperbaiki bug tersebut agar fitur kembali berfungsi normal.

### Masalah yang Ditemukan
1. **Bug Halaman Utama/Dashboard**: Menu dashboard tidak memuat data.
2. **Missing Loading States**: Indikator loading tidak muncul, sehingga halaman terasa mati/hang saat proses fetch data.
3. **Broken API Endpoints**: Beberapa endpoint API dipanggil oleh frontend tetapi tidak ditemukan atau menghasilkan error 404/500 di sisi backend.
4. **JS Error**: Ada error di console browser yang menghentikan eksekusi script `loaders.js` atau `app.js`.

### Scope Pekerjaan
Fokus perbaikan:
- `app/api/routes.py`: Pastikan endpoint API sudah terdaftar dan mengembalikan data yang benar.
- `app/static/js/loaders.js`: Perbaiki fungsi fetch data dan pastikan error handling (try-catch) berjalan.
- `app/static/js/app.js`: Cek inisialisasi aplikasi dan pastikan tidak ada conflict.
- `app/templates/`: Pastikan template memanggil script yang benar.

### Langkah Pengerjaan
1. **Analisis Error**: Buka Console browser, catat semua error `404` atau `Uncaught TypeError`.
2. **Perbaiki API**: Cek `app/api/routes.py` untuk route yang sering error/not found.
3. **Perbaiki Loader**: Update `app/static/js/loaders.js` agar:
   - Menampilkan loading spinner (jika belum ada).
   - Menangani error saat fetch (fetch gagal → pesan error muncul di UI, bukan di console saja).
4. **Validasi**: Jalankan aplikasi, buka semua menu satu persatu, pastikan data muncul dan tidak ada error di console.

### Acceptance Criteria
- [ ] Semua menu dapat memuat data kembali.
- [ ] Indikator loading muncul saat data sedang diambil.
- [ ] Tidak ada error merah di Console browser saat berpindah antar menu.
- [ ] UI konsisten (tidak ada elemen yang hilang secara tiba-tiba).

### Catatan Junior
- Jika stuck, cek apakah backend sudah running di port yang benar (port 8001).
- Pastikan perubahan di frontend (JS) selaras dengan struktur data dari API.
