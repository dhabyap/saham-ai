# AI Stock Analyzer Indonesia

Analisa saham IDX secara otomatis dengan AI, Telegram Bot, Dashboard Web, dan Sistem Pembelajaran (Machine Learning).

---

## Daftar Isi

- [Fitur](#fitur)
- [Tech Stack](#tech-stack)
- [Cara Install](#cara-install)
- [Konfigurasi](#konfigurasi)
- [Cara Menjalankan](#cara-menjalankan)
- [Dashboard](#dashboard)
- [Telegram Bot](#telegram-bot)
- [AI Learning System](#ai-learning-system)
- [API Endpoints](#api-endpoints)
- [Struktur Project](#struktur-project)
- [Deploy ke VPS](#deploy-ke-vps)
- [Troubleshooting](#troubleshooting)
- [Catatan](#catatan)

---

## Fitur

### Analisa Saham
- **Technical Indicators** - RSI, MACD, MA20, MA50, Support & Resistance
- **AI Analysis** - Analisa menggunakan OpenAI / Gemini / Ollama (local)
- **Rule-Based Engine** - Analisa otomatis tanpa API key
- **Chart Interaktif** - Candlestick, RSI, MACD, Volume (Chart.js)
- **Chart Image** - Generate chart PNG via mplfinance

### Market Overview
- **Fear & Greed Index** - Indeks sentimen pasar Indonesia
- **Top Gainer/Loser** - Saham naik/turun terbesar
- **Top Volume** - Saham dengan volume tertinggi
- **Sector Performance** - Performa per sektor industri
- **Market Summary** - Ringkasan advancing/declining

### Telegram Bot
- **Analisa Realtime** - Kirim analisa saham via Telegram
- **Watchlist** - Pantau saham favorit
- **Alert Notifikasi** - Notifikasi RSI, MACD, Volume spike
- **Feedback System** - Beri feedback untuk pembelajaran AI
- **Performance Monitoring** - Cek skor akurasi AI

### AI Learning & Self Improvement
- **Memory System** - Belajar dari histori prediksi
- **Auto Evaluation** - Evaluasi otomatis benar/salah prediksi
- **Adaptive Weights** - Bobot indikator menyesuaikan otomatis
- **Machine Learning** - Training model (RandomForest, XGBoost, LightGBM)
- **Backtesting** - Uji strategi dengan data historis
- **Knowledge Base** - Basis pengetahuan saham Indonesia

---

## Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Backend | FastAPI (Python 3.10+) |
| Database | SQLite (sqlite3) |
| Data Saham | yfinance (.JK) |
| AI | OpenAI / Gemini / Ollama |
| Telegram | python-telegram-bot |
| Charts | Chart.js (web), mplfinance (image) |
| ML | scikit-learn, xgboost, lightgbm |
| Scheduler | APScheduler |
| UI | Bootstrap 5 Dark Mode |

---

## Cara Install

### 1. Clone & Setup Virtual Environment

```bash
git clone <repository-url>
cd analisa-saham

# Buat virtual environment
python -m venv venv

# Aktivasi (Windows)
venv\Scripts\activate

# Aktivasi (Mac/Linux)
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Untuk fitur Machine Learning (opsional):
```bash
pip install scikit-learn xgboost lightgbm
```

### 3. Konfigurasi

```bash
cp .env.example .env
```

Edit file `.env` dan isi konfigurasi yang diperlukan. Lihat bagian [Konfigurasi](#konfigurasi).

### 4. Jalankan

```bash
python run.py
```

Buka browser: **http://localhost:8000**

---

## Konfigurasi

Seluruh konfigurasi ada di file `.env`:

### Telegram Bot
```
TELEGRAM_BOT_TOKEN=your_token_here
```
Dapatkan token dari [@BotFather](https://t.me/BotFather) di Telegram.

### AI Provider

Pilih salah satu provider AI:

**OpenAI:**
```
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
```

**Google Gemini:**
```
AI_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

**Ollama (Local/L Gratis):**
```
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### AI Learning
```
MIN_CONFIDENCE_THRESHOLD=50
DEFAULT_RISK_LEVEL=moderate
DEFAULT_STRATEGY=swing
```

### Server
```
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
SCHEDULER_INTERVAL=15
```

> **Tanpa API key?** Tidak masalah. Analisa tetap berjalan menggunakan rule-based engine.

---

## Cara Menjalankan

### Development Mode

```bash
python run.py
```

### Production Mode

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Background (screen/tmux)

```bash
screen -S stock
python run.py
# Ctrl+A, D untuk detach
screen -r stock  # untuk kembali
```

### URLs

| Halaman | URL |
|---------|-----|
| Dashboard | http://localhost:8000 |
| AI Settings | http://localhost:8000/ai-settings |
| AI Performance | http://localhost:8000/ai-performance |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

---

## Dashboard

### Trading Dashboard (`/`)
- Sidebar dengan daftar 25 saham IDX
- Chart interaktif (Close, MA20, MA50) dengan periode 1M/3M/6M/1Y
- Ringkasan: Price, RSI, MACD, Recommendation
- Panel analisa detail: Trend, Support, Resistance, Volume
- Chart RSI, MACD, dan Volume

### AI Settings (`/ai-settings`)
- **Risk Level** - Conservative / Moderate / Aggressive
- **Strategy Mode** - Scalping / Swing Trade / Long Term / Dividend
- **Indicator Weights** - Atur bobot RSI, MACD, Volume, Trend, Sentiment, S/R
- **Confidence Threshold** - Batas minimal confidence rekomendasi
- **Auto Learning** - Aktifkan pembelajaran otomatis
- **Custom Prompt** - Edit prompt AI langsung dari dashboard

### AI Performance (`/ai-performance`)
- **Metric Cards** - 7d Accuracy, 30d Accuracy, Overall, Winrate, Avg Profit
- **Accuracy Chart** - Grafik akurasi dari waktu ke waktu
- **Recent Predictions** - Daftar prediksi terbaru dengan hasil
- **Training Logs** - Log hasil training model ML
- **Strategy Comparison** - Perbandingan performa strategi
- **Backtesting** - Uji strategi dengan data historis

---

## Telegram Bot

Bot otomatis berjalan saat aplikasi dijalankan. Pastikan `TELEGRAM_BOT_TOKEN` terisi.

### Commands Analisa

| Command | Deskripsi |
|---------|-----------|
| `/start` | Mulai bot, lihat daftar command |
| `/analyze BBCA` | Analisa detail + chart saham BBCA |
| `/help` | Bantuan semua command |

### Commands Watchlist

| Command | Deskripsi |
|---------|-----------|
| `/add BBCA` | Tambah BBCA ke watchlist |
| `/remove BBCA` | Hapus BBCA dari watchlist |
| `/watchlist` | Lihat semua watchlist |

### Commands Market

| Command | Deskripsi |
|---------|-----------|
| `/topgainer` | Top 10 saham naik terbesar |
| `/toploser` | Top 10 saham turun terbesar |
| `/topvolume` | Top 10 saham volume tertinggi |
| `/market` | Ringkasan market (advancing/declining) |
| `/sentiment` | Sentimen market (Bullish/Bearish) |

### Commands AI Learning

| Command | Deskripsi |
|---------|-----------|
| `/feedback benar BBCA` | Beri feedback prediksi benar |
| `/feedback salah BBCA` | Beri feedback prediksi salah |
| `/feedback bullish BBCA` | Setiment bullish |
| `/feedback bearish BBCA` | Setiment bearish |
| `/accuracy` | Skor akurasi AI saat ini |
| `/performance` | Ringkasan performa AI |
| `/strategy` | Lihat mode strategi tersedia |

---

## AI Learning System

### Cara Kerja

```
┌──────────────────────────────────────────────────────────────┐
│                    AI LEARNING FLOW                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User/Auto  ──►  AI Analisa Saham                        │
│                                                              │
│  2. Prediksi disimpan ke database                           │
│     (stock, prediction, confidence, price)                  │
│                                                              │
│  3. Scheduler monitor hasil market setiap interval          │
│     (harga aktual vs prediksi)                              │
│                                                              │
│  4. Evaluasi: benar/salah, profit/loss                      │
│                                                              │
│  5. Update model scores: accuracy, winrate, avg profit      │
│                                                              │
│  6. Auto adjust: bobot indikator menyesuaikan               │
│     - Jika RSI sering salah → turunkan weight RSI           │
│     - Jika volume spike benar → naikkan weight Volume       │
│                                                              │
│  7. Rekomendasi berikutnya lebih akurat                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Memory System

Data yang disimpan untuk pembelajaran:

| Tabel | Fungsi |
|-------|--------|
| `ai_predictions` | Semua prediksi AI (stock, rec, confidence, hasil) |
| `ai_feedback` | Feedback user (benar/salah/bullish/bearish) |
| `ai_user_configs` | Konfigurasi per user (risk, strategy) |
| `ai_indicator_weights` | Bobot adaptif setiap indikator |
| `ai_model_scores` | Skor akurasi (7d, 30d, overall, winrate) |
| `ai_knowledge_base` | Basis pengetahuan saham |
| `ai_strategies` | Strategi trading tersedia |
| `ai_prompts` | Prompt custom untuk AI |
| `ai_training_logs` | Log hasil training ML |

### Indicator Weights

Bobot indikator otomatis menyesuaikan berdasarkan performa histori:

| Indikator | Default | Deskripsi |
|-----------|---------|-----------|
| RSI Weight | 1.0 | Bobot Relative Strength Index |
| MACD Weight | 1.0 | Bobot Moving Average Convergence Divergence |
| Volume Weight | 1.0 | Bobot analisa volume |
| Trend Weight | 1.0 | Bobot tren harga |
| Sentiment Weight | 1.0 | Bobot sentimen pasar |
| S/R Weight | 1.0 | Bobot Support & Resistance |

### Strategy Modes

| Mode | Target | Holding Period | Risk |
|------|--------|----------------|------|
| Scalping | 0.1-0.5% | Intraday | High |
| Swing Trade | 5-15% | Hari-Minggu | Moderate |
| Long Term | Pertumbuhan | Bulan-Tahun | Low |
| Dividend | Dividen | Bulan-Tahun | Low |

### Machine Learning Training

Jalankan training model dari API:

```bash
# RandomForest
curl -X POST http://localhost:8000/api/learning/train \
  -H "Content-Type: application/json" \
  -d '{"model_type": "random_forest", "period": "6mo"}'

# XGBoost (perlu install xgboost)
curl -X POST http://localhost:8000/api/learning/train \
  -H "Content-Type: application/json" \
  -d '{"model_type": "xgboost", "period": "6mo"}'
```

### Backtesting

```bash
curl "http://localhost:8000/api/learning/backtest/BBCA?strategy=swing&period=6mo"
```

Response:
```json
{
  "stock_code": "BBCA",
  "strategy": "swing",
  "total_trades": 12,
  "wins": 8,
  "losses": 4,
  "winrate": 66.67,
  "total_return_pct": 15.3,
  "avg_return_pct": 1.28
}
```

---

## API Endpoints

### Core API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/health` | Health check |
| GET | `/api/stocks` | Daftar semua saham |
| GET | `/api/stock/{code}` | Data saham + history |
| GET | `/api/analyze/{code}` | Analisa saham lengkap |
| GET | `/api/chart/{code}` | Generate chart PNG |
| GET | `/api/market-summary` | Ringkasan market |
| GET | `/api/market-sentiment` | Sentimen market |
| GET | `/api/sector-performance` | Performa sektor |
| GET | `/api/top-gainers` | Top gainer |
| GET | `/api/top-losers` | Top loser |
| GET | `/api/top-volume` | Top volume |
| GET | `/api/watchlist/{user_id}` | Watchlist user |
| GET | `/api/analysis-history` | Histori analisa |
| GET | `/api/alerts` | Log alerts |
| POST | `/api/watchlist/add` | Tambah watchlist |
| POST | `/api/watchlist/remove` | Hapus watchlist |

### AI Learning API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/learning/predictions` | Semua prediksi |
| GET | `/api/learning/predictions/{id}` | Detail prediksi |
| POST | `/api/learning/evaluate` | Evaluasi prediksi |
| GET | `/api/learning/performance` | Performa AI |
| GET | `/api/learning/scores` | Skor model |
| GET | `/api/learning/accuracy-chart` | Data chart akurasi |
| GET | `/api/learning/config/{user_id}` | Konfigurasi user |
| PUT | `/api/learning/config` | Update konfigurasi |
| GET | `/api/learning/weights/{user_id}` | Bobot indikator |
| PUT | `/api/learning/weights` | Update bobot |
| POST | `/api/learning/weights/adjust` | Auto adjust bobot |
| POST | `/api/learning/feedback` | Kirim feedback |
| GET | `/api/learning/feedback` | Semua feedback |
| GET | `/api/learning/feedback/stats` | Statistik feedback |
| GET | `/api/learning/knowledge/search` | Cari knowledge base |
| GET | `/api/learning/knowledge/categories` | Kategori knowledge |
| GET | `/api/learning/strategies` | Daftar strategi |
| GET | `/api/learning/prompts` | Daftar prompt |
| PUT | `/api/learning/prompts/{name}` | Update prompt |
| POST | `/api/learning/train` | Training model ML |
| GET | `/api/learning/training/logs` | Log training |
| GET | `/api/learning/backtest/{code}` | Backtest strategi |
| POST | `/api/learning/knowledge/seed` | Seed knowledge base |
| GET | `/api/learning/providers` | Provider AI tersedia |

Dokumentasi API lengkap: **http://localhost:8000/docs**

---

## Struktur Project

```
analisa-saham/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Konfigurasi dari .env
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # API endpoints utama
│   │   └── learning_routes.py     # API endpoints AI learning
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stock_service.py       # Data saham & indikator teknikal
│   │   ├── analysis_service.py    # Engine analisa (rule-based + AI)
│   │   └── market_service.py      # Market overview & sentimen
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── ai_analyzer.py         # AI analyzer (provider abstraction)
│   │   ├── learning_engine.py     # Self Learning Engine
│   │   ├── training_engine.py     # ML Training Pipeline
│   │   ├── knowledge_base.py      # Knowledge base & seed data
│   │   ├── providers/
│   │   │   ├── __init__.py        # Provider factory
│   │   │   ├── openai_provider.py # OpenAI API
│   │   │   ├── gemini_provider.py # Gemini API
│   │   │   └── ollama_provider.py # Ollama (local LLM)
│   │   └── prompts/
│   │       ├── analyst_prompt.txt # Prompt analisa
│   │       ├── risk_prompt.txt    # Prompt risiko
│   │       └── sentiment_prompt.txt # Prompt sentimen
│   │
│   ├── telegram/
│   │   ├── __init__.py
│   │   └── bot.py                 # Telegram bot handler
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── scheduler.py           # APScheduler config
│   │   └── tasks.py               # Scheduled tasks
│   │
│   ├── charts/
│   │   ├── __init__.py
│   │   └── chart_generator.py     # Generate chart images
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py            # DB connection & init (16 tabel)
│   │   ├── crud.py                # CRUD operasi utama
│   │   └── ai_crud.py             # CRUD operasi AI learning
│   │
│   ├── templates/
│   │   ├── dashboard.html         # Trading dashboard
│   │   ├── ai_settings.html       # AI Settings panel
│   │   └── ai_performance.html    # AI Performance dashboard
│   │
│   └── static/
│       ├── style.css              # Dark mode CSS
│       ├── dashboard.js           # Chart.js dashboard
│       └── charts/                # Generated chart images
│
├── run.py                         # Main runner
├── test_app.py                    # Integration test
├── requirements.txt               # Python dependencies
├── .env.example                   # Template konfigurasi
├── .env                           # Konfigurasi (buat sendiri)
└── README.md
```

---

## Deploy ke VPS

### 1. Setup Server

```bash
# Install Python 3.10+
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Clone repo
git clone <repository-url>
cd analisa-saham

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Konfigurasi

```bash
nano .env
# Isi TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, dll
```

### 3. Jalankan dengan Systemd

```bash
sudo nano /etc/systemd/system/stock-analyzer.service
```

```ini
[Unit]
Description=AI Stock Analyzer Indonesia
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/analisa-saham
ExecStart=/path/to/analisa-saham/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable stock-analyzer
sudo systemctl start stock-analyzer
sudo systemctl status stock-analyzer
```

### 4. Nginx Reverse Proxy (opsional)

```nginx
server {
    listen 80;
    server_name stock.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Troubleshooting

### Error: "No module named 'telegram'"
```bash
pip install python-telegram-bot
```

### Error: "yfinance returned no data for..."
- Pastikan koneksi internet aktif
- Coba kode saham lain (contoh: BBCA, BBRI, TLKM)
- Data hanya tersedia untuk hari trading (Senin-Jumat)

### Error: "AI analysis tidak tersedia"
- Pastikan API key terisi di `.env`
- Cek `AI_PROVIDER` sesuai dengan key yang diisi
- Tanpa API key, analisa tetap jalan dengan rule-based

### Database tidak bisa ditulis
- Pastikan folder `app/database/` ada dan punya hak tulis
- Database SQLite otomatis dibuat saat pertama kali dijalankan

### Scheduler tidak jalan
- Cek log terminal untuk pesan error
- Pastikan `SCHEDULER_INTERVAL` bernilai positif (menit)

### Telegram bot tidak aktif
- Pastikan `TELEGRAM_BOT_TOKEN` terisi di `.env`
- Token bisa didapat dari [@BotFather](https://t.me/BotFather)

---

## Catatan

- Data saham menggunakan **yfinance** dengan kode `.JK` (contoh: BBCA.JK)
- Data hanya tersedia saat market hours dan hari trading
- Fitur AI membutuhkan **API key** (OpenAI/Gemini) atau **Ollama** (local)
- Tanpa API key, analisa tetap berjalan menggunakan **rule-based engine**
- Telegram bot **tidak wajib** - fitur utama tetap berjalan tanpa bot
- Database SQLite otomatis dibuat saat pertama kali dijalankan
- Training ML membutuhkan paket `scikit-learn` (install manual)
- XGBoost dan LightGBM bersifat opsional untuk training lebih akurat

---

## Lisensi

MIT License
