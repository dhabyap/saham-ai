# Tugas 3: Revamp Scoring System

## Target

Buat **scoring engine** baru yang menerapkan bobot persis sesuai METODE_ANALISIS.md. Pisahkan dari learning_engine agar lebih modular.

---

## Bobot Scoring (dari METODE_ANALISIS.md)

| Komponen | Bobot | Sumber Data |
|----------|-------|-------------|
| Foreign Flow | 35% | foreign_flow service (Tugas 2) |
| Accumulation / Distribution | 25% | foreign_flow service (Tugas 2) |
| Relative Strength | 15% | relative_strength service (Tugas 1) |
| Technical | 10% | stock_service (indikator existing) |
| Sector Rotation | 10% | market_service (existing) |
| Sentiment / Risk | 5% | rule-based + AI |

---

## Bagian A: Scoring Engine

### File Baru: `app/ai/scoring_engine.py`

```python
from typing import Optional, Literal
from dataclasses import dataclass, asdict

StrategyType = Literal["swing", "day_trade", "long_term"]
RiskLevel = Literal["low", "moderate", "high"]
```

### Struct: ScoringResult

```python
@dataclass
class ScoringComponent:
    name: str
    weight: float        # 0.0 - 1.0 (sesuai bobot)
    score: float         # 0 - 100
    weighted_score: float  # score * weight
    reason: str          # penjelasan kenapa dapet nilai ini
    data_source: str     # dari mana data diambil

@dataclass
class ScoringResult:
    stock_code: str
    strategy: StrategyType
    risk_level: RiskLevel
    components: list[ScoringComponent]
    total_score: float        # 0 - 100
    recommendation: str       # "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"
    confidence: float         # 0 - 100
    summary: str              # 1 paragraf kesimpulan
    risks: list[str]          # list risiko
    catalysts: list[str]      # list katalis positif
    last_updated: str
```

### Fungsi 1: `score_technical(df: pd.DataFrame) -> ScoringComponent`

**Logic:**
Gunakan indikator yang sudah ada dari `stock_service.calculate_indicators()`:

| Kondisi | Score |
|---------|-------|
| RSI 30-70 (normal) | +20 |
| RSI oversold (<30) + MACD golden cross | +40 |
| RSI overbought (>70) | -20 |
| MACD bullish + histogram positif | +20 |
| MACD golden cross baru | +30 |
| MACD death cross baru | -30 |
| Harga > MA20 > MA50 (bullish alignment) | +20 |
| Harga < MA20 < MA50 (bearish alignment) | -20 |
| Volume > 1.5x rata-rata (spike) | +15 |
| Harga dekat support | +10 |
| Harga dekat resistance | -10 |

Score akhir: jumlah semua poin, clamp ke 0-100.

### Fungsi 2: `score_foreign_flow(stock_code: str) -> ScoringComponent`

**Logic:**
Ambil data dari foreign_flow service:

| Kondisi | Score |
|---------|-------|
| Accumulating (3+ hari net buy) | +40 |
| Strong accumulation (5+ hari, strength=strong) | +60 |
| Distributing (3+ hari net sell) | -30 |
| Strong distribution (5+ hari, strength=strong) | -50 |
| Net 5 hari positif | +20 |
| Net 5 hari negatif | -20 |
| Net 20 hari positif | +15 |
| Net 20 hari negatif | -15 |
| Foreign net > 50% total volume | +25 |
| Foreign net < -50% total volume | -25 |
| Tidak ada data foreign flow | +0 (score = 0, neutral) |

Score akhir: jumlah semua poin, clamp ke 0-100.

### Fungsi 3: `score_accumulation(stock_code: str) -> ScoringComponent`

**Logic:**
Analisis lebih dalam dari data akumulasi (Tugas 2):

| Kondisi | Score |
|---------|-------|
| accumulation_days >= 5 | +50 |
| accumulation_days >= 3 | +30 |
| distribution_days >= 5 | -50 |
| distribution_days >= 3 | -30 |
| avg_net_5d > avg_net_20d (percepatan) | +20 |
| avg_net_5d < avg_net_20d (perlambatan) | -15 |
| strength = "strong" | +15 |
| Harga naik + foreign net buy (konfirmasi) | +15 |
| Harga turun + foreign net buy (akumulasi tersembunyi) | +25 |

### Fungsi 4: `score_relative_strength(stock_code: str) -> ScoringComponent`

**Logic:**
Panggil `calculate_relative_strength(stock_code)`:

| Kondisi | Score |
|---------|-------|
| RS > 10 (strong outperforming) | +50 |
| RS > 5 (outperforming) | +30 |
| RS > 2 (slightly outperforming) | +15 |
| RS < -10 (strong underperforming) | -50 |
| RS < -5 (underperforming) | -30 |
| RS < -2 (slightly underperforming) | -15 |
| Selainnya (neutral) | +5 |

### Fungsi 5: `score_sector(stock_code: str) -> ScoringComponent`

**Logic:**
Panggil `market_service.get_sector_flow()`:

| Kondisi | Score |
|---------|-------|
| Sector = inflow | +30 |
| Sector = top performer | +40 |
| Sector = outflow | -20 |
| Sector = worst performer | -30 |
| Neutral sector | +5 |

Mapping sector dari `stock_service.STOCK_LIST` + `market_service.sector_map` (existing).

### Fungsi 6: `score_sentiment(stock_code: str, risk_level: RiskLevel) -> ScoringComponent`

**Logic:**
Berdasarkan risk level user + kondisi teknikal:

| Kondisi | Score |
|---------|-------|
| Risk = low + RSI normal + trend bullish | +30 |
| Risk = low + RSI overbought | -20 |
| Risk = high + oversold + accumulation | +40 |
| Risk = high + volume spike | +20 |
| Trend bearish + distribution | -30 |

### Fungsi 7: `calculate_score(
    stock_code: str,
    strategy: StrategyType = "swing",
    risk_level: RiskLevel = "moderate",
    df: Optional[pd.DataFrame] = None
) -> ScoringResult`

**Logic:**
1. Ambil df dari `fetch_stock_data()` atau parameter
2. Hitung indikator via `calculate_indicators(df)` jika perlu
3. Panggil semua fungsi scoring (1-6)
4. Hitung total_score = SUM(weighted_score)
5. Tentukan recommendation:
   - >= 80: "STRONG_BUY"
   - >= 65: "BUY"
   - >= 45: "HOLD"
   - >= 30: "SELL"
   - < 30: "STRONG_SELL"
6. Tentukan confidence = total_score (confidence = seberapa yakin)
7. Generate summary otomatis dari komponen dengan score tertinggi/terendah
8. Generate risks & catalysts dari komponen negatif/positif
9. Return ScoringResult

**Catatan penting untuk STRATEGY:**
- Jika strategy = "day_trade": **double weight** untuk komponen technical (jadi 20%), kurangin relative strength weight jadi 10%
- Jika strategy = "long_term": **double weight** untuk accumulation/distribution (jadi 50%), kurangin technical weight jadi 5%

---

## Bagian B: Integrasi ke Analysis Service

### Modifikasi: `app/services/analysis_service.py`

**Ganti logic `analyze_stock()`:**
1. Panggil `ScoringEngine.calculate_score()` sebagai default analysis
2. AI analysis tetap jadi OPSIONAL (hanya jika `use_ai=True`)
3. Jika AI aktif, AI menerima `ScoringResult` sebagai context tambahan
4. Simpan prediksi seperti biasa

### Fungsi baru di class `AnalysisService`:

```python
def analyze_stock_scored(self, code, strategy="swing", risk_level="moderate"):
    """Murni pake scoring engine, tanpa AI. Untuk mode offline/cepat."""
    scoring = ScoringEngine()
    result = scoring.calculate_score(code, strategy, risk_level)
    return {
        "stock_code": result.stock_code,
        "recommendation": result.recommendation,
        "confidence": result.confidence,
        "score": result.total_score,
        "components": [asdict(c) for c in result.components],
        "summary": result.summary,
        "risks": result.risks,
        "catalysts": result.catalysts,
        "source": "scoring_engine",
    }
```

---

## Bagian C: Endpoint API Baru

### Modifikasi: `app/api/routes.py`

### `GET /api/scored-analysis/{code}`
Analisis pake scoring engine.

Query params opsional: `strategy` (default "swing"), `risk_level` (default "moderate").

**Response:**
```json
{
    "status": "ok",
    "data": {
        "stock_code": "BBCA",
        "recommendation": "BUY",
        "confidence": 72,
        "total_score": 72.5,
        "components": [
            {"name": "Foreign Flow", "weight": 0.35, "score": 80, "weighted_score": 28, "reason": "Accumulating 5 hari berturut-turut"},
            {"name": "Accumulation", "weight": 0.25, "score": 75, "weighted_score": 18.75, "reason": "Strong accumulation, avg net positif"},
            {"name": "Relative Strength", "weight": 0.15, "score": 65, "weighted_score": 9.75, "reason": "Outperforming IHSG"},
            {"name": "Technical", "weight": 0.10, "score": 70, "weighted_score": 7, "reason": "RSI normal, MACD bullish"},
            {"name": "Sector", "weight": 0.10, "score": 80, "weighted_score": 8, "reason": "Financial sector inflow"},
            {"name": "Sentiment", "weight": 0.05, "score": 60, "weighted_score": 3, "reason": "Moderate risk, trend stable"}
        ],
        "summary": "BBCA menunjukkan akumulasi asing kuat dengan 5 hari net buy berturut-turut...",
        "risks": ["Harga mendekati resistance", "IHSG sedang koreksi ringan"],
        "catalysts": ["Foreign accumulation konsisten", "Sektor financial inflow"],
        "strategy": "swing",
        "risk_level": "moderate",
        "last_updated": "2026-06-05T09:00:00"
    }
}
```

---

## Bagian D: Testing

### File Baru: `tests/test_scoring_engine.py`

1. Test `ScoringEngine.calculate_score("BBCA")` — assert return ScoringResult dengan semua field valid
2. Test scoring untuk strategy="day_trade" — assert bobot technical lebih besar
3. Test scoring untuk strategy="long_term" — assert bobot accumulation lebih besar
4. Test tiap komponen scoring individual dengan mock data

---

## Kriteria Selesai

- [ ] `scoring_engine.py` dengan 7 fungsi scoring
- [ ] `calculate_score()` return `ScoringResult` lengkap
- [ ] Bobot berubah sesuai strategy (swing/day_trade/long_term)
- [ ] Analysis service pake scoring engine sebagai default
- [ ] Endpoint `/api/scored-analysis/{code}` return JSON valid
- [ ] Test file jalan

---
