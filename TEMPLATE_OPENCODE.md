# OpenCode Task Template

## Format Output Wajib

Setiap task yang dikerjakan OpenCode HARUS mengikuti standar ini agar konsisten.

---

## 1. Code Style

- **Indentasi:** 4 spasi (NO tabs)
- **String:** double quotes `""` untuk Python (`"text"`, bukan `'text'`)
- **Naming:** `snake_case` untuk fungsi/variabel, `PascalCase` untuk class
- **Type hints:** WAJIB di semua fungsi + parameter + return
- **Docstring:** WAJIB — format Google style:

```python
def fetch_data(code: str, days: int = 30) -> Optional[pd.DataFrame]:
    """Fetch stock data from Yahoo Finance.

    Args:
        code: Stock code (e.g. "BBCA")
        days: Number of historical days to fetch

    Returns:
        DataFrame with OHLCV data, or None if failed
    """
    pass
```

- **Error handling:** SEMUA fungsi harus handle error, jangan biarkan crash
- **Return None** on failure, jangan raise exception kecuali fatal
- **Logging:** pakai `print()` dengan prefix emoji, jangan `logging`

---

## 2. File Structure

### Service files (`app/services/*.py`)
- 1 class per file (kecuali helper kecil)
- Class name: `PascalCase` + `Service` (e.g. `IHSGService`)
- Method name: `snake_case`
- Import internal modules di dalem fungsi (lazy import) untuk hindari circular import

### Strategy files (`app/ai/strategies/*.py`)
- 1 class per file
- Method utama: `analyze()`, `get_entry_signal()`, `get_exit_signal()`
- Return type: `dict` dengan field konsisten, jangan pake objek custom (biar JSON-ready)

### Database files (`app/database/*.py`)
- Fungsi standalone (bukan class) — `init_*_db()`, `save_*()`, `get_*()`
- Panggil `init_*_db()` di module level supaya tabel auto-created saat import
- SQL: `INSERT OR REPLACE` (bukan `INSERT OR IGNORE` kecuali perlu)
- Koneksi: ambil dari `app.database.database.get_db()`

### Route files (`app/api/routes.py`)
- Tambah import di DALEM fungsi endpoint (lazy import) untuk hindari circular
- Format endpoint:
```python
@router.get("/api/example/{param}")
async def example_endpoint(param: str, query_param: str = "default"):
    from app.services.example import ExampleService
    data = ExampleService().do_something(param, query_param)
    return {"status": "ok", "data": data}
```
- Status: selalu `"ok"` untuk sukses
- Error: jangan return error page, return `{"status": "error", "message": "..."}`

### Test files (`tests/test_*.py`)
- 1 file per service/feature
- Nama fungsi: `test_*()` (wajib prefix `test_`)
- 3-5 test per file
- Test real API calls (timeout 30s), bukan mock
- Assert value, type, dan field existence

---

## 3. Git Workflow

Setiap perubahan HARUS:
1. Di branch terpisah: `feature/task-{N}-{nama}`
2. Commit message: `feat: Deskripsi singkat` atau `fix: Deskripsi singkat`
3. Setelah selesai: `git add -A && git commit -m "..." && git push`
4. PR via `gh pr create`

---

## 4. Verification Wajib

Selesai coding, HARUS jalanin:
1. `python -c "import py_compile; py_compile.compile('file.py', doraise=True)"` — syntax check
2. `python -m pytest tests/test_*.py -v --tb=short` — test jalan
3. `python -c "import sys; sys.path.insert(0, '.'); from app.main import app; print('OK')"` — import check

Laporkan hasil verifikasi di akhir output.

---

## 5. Output Report Format

Setelah selesai, report WAJIB format:

```
## Files Created/Modified
- `path/file.py` — Deskripsi singkat (N lines)
- ...

## Test Results
N/N passed (X.XXs)

## Verification
- Syntax check: OK
- Import check: OK

## Notes
- ... (special cases, potential issues, known limitations)
```
