# Setup Wizard & CLI Manager Guide

Interactive CLI Setup Wizard dan Configuration Management System untuk AI Stock Analyzer.

## Quick Start

### 1. Initial Setup (First Time)

Jika ini pertama kali menjalankan aplikasi:

```bash
# Option A: Menggunakan setup.py
python setup.py

# Option B: Langsung jalankan run.py (auto detect first run)
python run.py

# Option C: Jalankan setup wizard manual
python cli/setup_wizard.py
```

Sistem akan otomatis:
- ✓ Mendeteksi jika belum ada konfigurasi
- ✓ Menjalankan Setup Wizard interaktif
- ✓ Membuat file `.env`
- ✓ Membuat file `config/settings.json`
- ✓ Membuat folder yang diperlukan
- ✓ Test semua koneksi

### 2. Manage Configuration

Edit konfigurasi yang sudah ada:

```bash
python cli/config.py
```

Fitur:
- View current configuration
- Edit AI Provider
- Change API keys
- Modify Telegram settings
- Change database
- Edit risk mode
- Test connections
- Reset configuration

### 3. CLI Manager (Main Menu)

Kelola aplikasi dari satu tempat:

```bash
python cli/manage.py
```

Menu options:
- Start Web Server
- Start Telegram Bot
- Start Scheduler
- Run AI Training
- View Logs
- Manage Configuration
- Setup Wizard
- View Application Info
- Install Dependencies
- Exit

## Setup Wizard Flow

### Step-by-Step Process

#### [1/10] Pilih AI Provider
```
1. OpenAI
2. Gemini (Google)
3. Ollama (Local)
```

#### [2/10] Setup Provider Credentials
Masukkan API key berdasarkan provider yang dipilih:
- OpenAI: GPT-4 Turbo (default)
- Gemini: Gemini 2.0 Flash (default)
- Ollama: Local API endpoint

#### [3/10] Gunakan Telegram Bot?
Konfigurasi Telegram Bot untuk notifikasi:
- Telegram Bot Token
- Chat ID (untuk menerima pesan)

#### [4/10] Pilih Database
```
1. SQLite (Default, local)
2. PostgreSQL (Production)
```

#### [5/10] Enable Auto Learning?
Aktifkan sistem pembelajaran otomatis AI:
- Y: AI akan terus belajar dari data
- N: Manual training only

#### [6/10] Pilih Risk Mode
```
1. Conservative - Fokus keamanan, return rendah
2. Moderate - Balanced risk & return (Default)
3. Aggressive - High risk, high return
```

#### [7/10] Interval Monitoring
Set berapa menit sistem check stock:
- Default: 15 menit
- Min: 1 menit
- Max: 1440 menit (24 jam)

#### [8/10] Enable Ollama Local Fallback?
Gunakan Ollama sebagai fallback jika API provider down:
- Y: Setup local AI fallback
- N: Gunakan cloud API saja

#### [9/10] Konfigurasi Tambahan
- Min Confidence Threshold (0-100)
- App Port (default: 8000)
- Debug Mode (Y/N)

#### [10/10] Review & Save
- Review semua konfigurasi
- Confirm untuk simpan
- Auto test semua koneksi
- Create required directories

## Generated Files

### .env (Sensitive Config)
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=xxxxx
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4-turbo
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=123456789
DATABASE_URL=sqlite:///app/database/stock.db
DATABASE_PATH=app/database/stock.db
DATABASE_TYPE=sqlite
AUTO_LEARNING=true
RISK_MODE=moderate
SCHEDULER_INTERVAL=15
OLLAMA_ENABLED=true
MIN_CONFIDENCE_THRESHOLD=50
APP_PORT=8000
APP_HOST=0.0.0.0
DEBUG=true
DEFAULT_RISK_LEVEL=moderate
DEFAULT_STRATEGY=swing
```

### config/settings.json (Non-Sensitive)
```json
{
  "app_name": "AI Stock Analyzer",
  "app_version": "1.0.0",
  "auto_learning": true,
  "risk_mode": "moderate",
  "monitor_interval": 15,
  "ollama_enabled": false,
  "min_confidence_threshold": 50,
  "default_strategy": "swing",
  "max_portfolio_stocks": 10,
  "log_level": "INFO",
  "language": "id",
  "theme": "dark"
}
```

### Directories Created
- `logs/` - Application logs
- `app/database/` - Database storage
- `app/static/charts/` - Generated charts
- `config/` - Configuration files

## Validation System

### Input Validation Rules

| Input | Rule |
|-------|------|
| API Key | Min 5 chars, not empty |
| Token | Min 10 chars, not empty |
| Chat ID | Must be numeric (positive or negative) |
| Integer | Must be number, within range |
| URL | Must start with http:// or https:// |
| Yes/No | Must be 'y', 'n', 'yes', 'no' |
| Choice | Must be valid number in range |

### Error Handling

Jika input salah, sistem akan:
1. Tampilkan error message yang jelas
2. Minta input ulang
3. Lanjut ke step berikutnya jika valid

## Connection Testing

### Auto Test Features

Setelah setup selesai, sistem otomatis test:

✓ **AI Provider Connection**
- OpenAI API
- Gemini API
- Ollama Local

✓ **Telegram Bot**
- Bot token validity
- Connection test

✓ **Database**
- Database path exists
- Write permission

Display hasil:
```
[OK]    OpenAI API connection OK
[OK]    Telegram Bot connection OK
[OK]    SQLite database path OK
```

## Security Features

### Secure Input Handling

1. **Hidden Password Input**
   - API keys tidak ditampilkan di terminal
   - Menggunakan `getpass` module
   - Display **** saat typing

2. **Validation**
   - Format validation
   - Range checking
   - Type checking

3. **Safe Storage**
   - Sensitive data di `.env` (add to .gitignore)
   - Non-sensitive di `settings.json`

## Common Tasks

### Change AI Provider

```bash
python cli/config.py
# Select: Edit AI Provider
# Choose: New provider
```

### Update API Key

```bash
python cli/config.py
# Select: Edit API Keys
# Enter: New API key
```

### Edit Risk Mode

```bash
python cli/config.py
# Select: Edit Risk Mode
# Choose: conservative/moderate/aggressive
```

### Test All Connections

```bash
python cli/config.py
# Select: Test Connections
```

### Reset Configuration

```bash
python cli/config.py
# Select: Reset Configuration
# Confirm: Are you sure?
```

## Environment Variables

### Required (Must be set)

- `AI_PROVIDER` - openai, gemini, atau ollama
- API key untuk provider yang dipilih
- `DATABASE_URL` - Database connection string

### Optional

- `TELEGRAM_BOT_TOKEN` - Untuk Telegram bot
- `TELEGRAM_CHAT_ID` - Chat ID penerima pesan
- `AUTO_LEARNING` - true/false
- `RISK_MODE` - conservative, moderate, aggressive
- `SCHEDULER_INTERVAL` - Minutes (default: 15)
- `APP_PORT` - Port aplikasi (default: 8000)
- `DEBUG` - true/false (default: true)

## Troubleshooting

### Setup Wizard tidak muncul

**Problem**: Jalankan `python run.py` tidak auto start wizard

**Solution**:
```bash
# Manual jalankan wizard
python cli/setup_wizard.py
```

### API Connection Failed

**Problem**: "Connection test failed"

**Solution**:
1. Verify API key valid
2. Check internet connection
3. Verify API quota
4. Try test again di config editor

### Telegram Bot Error

**Problem**: "Telegram Bot connection failed"

**Solution**:
1. Verify bot token correct
2. Check @BotFather for token
3. Make sure bot is active
4. Check Telegram API status

### Database Error

**Problem**: Database file not created

**Solution**:
1. Verify path permissions
2. Ensure parent directory exists
3. Check disk space
4. Try reset config and setup again

## Advanced Configuration

### Use Environment File

Jika prefer edit `.env` manual:

```bash
# Create .env from template
cp .env.example .env

# Edit manually
nano .env

# Verify with config editor
python cli/config.py
```

### Multi-Profile Configuration

Future feature: Store multiple configs dengan nama berbeda
```bash
python cli/setup_wizard.py --profile production
python cli/setup_wizard.py --profile development
```

### Configuration Backup

```bash
# Backup current config
cp .env .env.backup
cp config/settings.json config/settings.json.backup

# Restore from backup
cp .env.backup .env
cp config/settings.json.backup config/settings.json
```

## CLI Commands Reference

### Setup Wizard

```bash
# First time setup
python setup.py

# Manual run wizard
python cli/setup_wizard.py

# Interactive setup dari run.py
python run.py  # (auto detect first run)
```

### Config Manager

```bash
# Open config editor
python cli/config.py
```

### CLI Manager

```bash
# Open main menu
python cli/manage.py

# Run specific command
python cli/manage.py --action start-server
python cli/manage.py --action test-connections
```

### Start Application

```bash
# Start web server (with auto setup if needed)
python run.py

# Start telegram bot
python -m app.telegram.bot

# Start scheduler
python -m app.scheduler.scheduler

# Run training
python -m app.ai.training_engine
```

## Dependencies

Setup wizard memerlukan packages:
- `rich` - Beautiful terminal output
- `questionary` - Interactive CLI questions
- `colorama` - Color terminal text
- `python-dotenv` - .env file management

Semua terinstall otomatis saat `python setup.py`

## Tips & Best Practices

1. **Save Credentials Safely**
   - Add `.env` ke `.gitignore`
   - Never commit API keys
   - Use config/settings.json untuk non-sensitive

2. **Regular Backups**
   - Backup `.env` jika ada perubahan
   - Store credentials di password manager
   - Document konfigurasi production

3. **Test After Setup**
   - Run test connections
   - Verify web server starts
   - Check logs untuk errors

4. **Update Configuration**
   - Edit via `cli/config.py` recommended
   - Manual edit `.env` jika needed
   - Test connections setelah perubahan

## Support & More Info

Untuk bantuan lebih lanjut:
- Baca README.md untuk overview
- Check logs/ untuk error details
- Run test connections untuk diagnostik
- Re-run setup wizard jika config corrupt

---

**Version**: 1.0.0
**Last Updated**: 2024
**Language**: Indonesian / English
