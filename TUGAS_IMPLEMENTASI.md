# Master Tugas Implementasi — Analisa Saham IDX

## Prioritas & Urutan Pengerjaan

| No | Tugas | Prioritas | Dependensi | Estimasi |
|----|-------|-----------|------------|----------|
| 1 | **Data IHSG + Relative Strength** | 🔴 WAJIB | Tidak ada | 2-3 hari |
| 2 | **Foreign Flow Data** | 🔴 WAJIB | Tidak ada | 3-4 hari |
| 3 | **Scoring System Revamp** | 🔴 WAJIB | No 1 + 2 | 2 hari |
| 4 | **BPJS Day Trading Strategy** | 🟡 LANJUTAN | No 1 + 2 + 3 | 4-5 hari |
| 5 | **Creative Trader Long Term** | 🟡 LANJUTAN | No 1 + 2 + 3 | 4-5 hari |

**WAJIB dikerjakan berurutan.** Task 4 dan 5 bisa dikerjakan paralel setelah task 3 selesai.

---

## Alur Data

```
Yahoo Finance ──→ stock_service ──→ scoring engine ──→ API ──→ Frontend
                     ↓                    ↑
RTI Business ──→ foreign_flow ─────────────┘
Yahoo Finance ──→ ihsg_service ────────────┘
```

---

## File yang Akan Dimodifikasi/Dibuat

| File | Status | Untuk Task |
|------|--------|------------|
| `app/services/ihsg_service.py` | BARU | 1 |
| `app/services/relative_strength.py` | BARU | 1 |
| `app/services/foreign_flow.py` | BARU | 2 |
| `app/ai/scoring_engine.py` | BARU | 3 |
| `app/ai/strategies/bpjs_strategy.py` | BARU | 4 |
| `app/ai/strategies/creative_trader_strategy.py` | BARU | 5 |
| `app/ai/strategies/__init__.py` | BARU | 4+5 |
| `app/services/stock_service.py` | MODIF | 1 |
| `app/services/analysis_service.py` | MODIF | 3 |
| `app/api/routes.py` | MODIF | 1+2 |
| `app/config.py` | MODIF | 2 |
| `app/ai/learning_engine.py` | MODIF | 3 |
| `.env.example` | MODIF | 2 |
| `requirements.txt` | MODIF | 2 |

---

## Convention Coding

1. **Docstring wajib** — tiap fungsi pake triple-quote English
2. **Type hints wajib** — tiap parameter dan return value
3. **Error handling** — jangan pernah `except: pass`, minimal log
4. **Test file** — tiap tugas wajib bikin `tests/test_<nama>.py`
5. **Import** — relative import `from app.services.x import y`
6. **Naming** — snake_case untuk fungsi/variabel, PascalCase untuk class
7. **Logging** — pake `print()` untuk dev, nanti upgrade ke logging module

---
