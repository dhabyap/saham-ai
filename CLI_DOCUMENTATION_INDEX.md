# CLI Setup System - Complete Documentation Index

Dokumentasi lengkap untuk Interactive CLI Setup Wizard dan Configuration Management System.

## 📚 Documentation Files

### Quick Start (Mulai dari sini!)
- **[QUICKSTART.md](QUICKSTART.md)** ⭐
  - Installation dalam 5 menit
  - Common tasks
  - Troubleshooting cepat
  - Demo flow

### Detailed Setup Guide
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)**
  - Complete setup flow
  - Feature explanations
  - Generated files reference
  - Advanced configuration
  - Security features

### CLI System Documentation
- **[cli/README.md](cli/README.md)**
  - Module structure
  - API reference
  - Class & function documentation
  - Usage examples
  - Best practices

## 🚀 Quick Commands

```bash
# First time setup (recommended)
python setup.py

# Or direct run
python run.py

# Edit configuration
python cli/config.py

# Open main menu
python cli/manage.py

# Test CLI system
python test_cli.py
```

## 📁 Project Structure

```
analisa-saham/
├── cli/                          # ← NEW: Interactive CLI System
│   ├── __init__.py
│   ├── setup_wizard.py          # Main setup wizard
│   ├── config.py                # Configuration editor
│   ├── manage.py                # CLI manager (main menu)
│   ├── validators.py            # Input validation
│   ├── helpers.py               # Helper utilities
│   └── README.md                # CLI documentation
│
├── config/                       # ← NEW: Configuration folder
│   └── settings.json            # Auto-generated settings
│
├── logs/                         # ← NEW: Logs folder
│   └── *.log
│
├── setup.py                      # ← NEW: Setup entry point
├── SETUP_GUIDE.md               # ← NEW: Setup documentation
├── QUICKSTART.md                # ← NEW: Quick start guide
├── test_cli.py                  # ← NEW: CLI test suite
├── .env.example                 # ← NEW: .env template
├── run.py                        # ← UPDATED: Auto setup
├── requirements.txt             # ← UPDATED: Added CLI deps
│
├── app/
│   ├── config.py
│   ├── database/                # ← Will be created
│   ├── static/
│   │   └── charts/
│   └── ...
│
└── README.md
```

## 📋 Feature Checklist

### Setup Wizard (10 Steps)
- [x] Choose AI Provider (OpenAI/Gemini/Ollama)
- [x] Get API Credentials
- [x] Setup Telegram Bot (optional)
- [x] Choose Database (SQLite/PostgreSQL)
- [x] Enable Auto Learning
- [x] Choose Risk Mode
- [x] Set Monitoring Interval
- [x] Enable Ollama Fallback (optional)
- [x] Additional Settings
- [x] Review & Save

### Configuration Management
- [x] View current config
- [x] Edit AI provider
- [x] Update API keys
- [x] Modify Telegram settings
- [x] Change database
- [x] Edit risk mode
- [x] Edit monitoring settings
- [x] Test connections
- [x] Reset configuration

### CLI Manager Menu
- [x] Start web server
- [x] Start Telegram bot
- [x] Start scheduler
- [x] Run AI training
- [x] View logs
- [x] Manage configuration
- [x] Setup wizard
- [x] View app info
- [x] Install dependencies

### Technical Features
- [x] Interactive CLI (questionary)
- [x] Input validation system
- [x] Secure password input
- [x] Auto .env generation
- [x] Auto settings.json generation
- [x] Directory creation
- [x] Connection testing
- [x] First run detection
- [x] Error handling & retry
- [x] Clean terminal UI (rich)

## 🎯 Usage Guide

### Scenario 1: Fresh Installation
```bash
# Method A (Recommended)
python setup.py

# Method B
python run.py

# Method C
python cli/setup_wizard.py
```

### Scenario 2: Edit Configuration
```bash
python cli/config.py
# Select option from menu
```

### Scenario 3: Manage Application
```bash
python cli/manage.py
# Navigate menu to perform tasks
```

### Scenario 4: Test System
```bash
python test_cli.py
# Verify all components work
```

## 🔐 Security

### Sensitive Data (.env)
- [x] Hidden from output
- [x] Added to .gitignore
- [x] Password input masked
- [x] Validation before save

### Non-Sensitive Data (settings.json)
- [x] Safe to version control
- [x] JSON format
- [x] Can be shared

## 📊 Statistics

| Component | Lines | Status |
|-----------|-------|--------|
| setup_wizard.py | 285 | ✅ Complete |
| config.py | 370 | ✅ Complete |
| manage.py | 330 | ✅ Complete |
| validators.py | 150 | ✅ Complete |
| helpers.py | 240 | ✅ Complete |
| CLI Docs | 300+ | ✅ Complete |
| Setup Guide | 400+ | ✅ Complete |
| Quick Start | 200+ | ✅ Complete |
| **Total** | **2275+** | ✅ Complete |

## 🚦 Getting Started (3 Steps)

### Step 1: Initial Setup
```bash
python setup.py
# Follow interactive wizard
# ~2 minutes
```

### Step 2: Verify Setup
```bash
python test_cli.py
# Check all components
# ~30 seconds
```

### Step 3: Start Application
```bash
python run.py
# Open http://localhost:8000
# Done!
```

## 📖 Documentation Map

```
Start Here
    ↓
QUICKSTART.md (5 min read)
    ↓
    ├─→ Try: python setup.py
    ├─→ Try: python cli/config.py
    └─→ Try: python cli/manage.py
    ↓
SETUP_GUIDE.md (detailed)
    ├─→ Understand setup flow
    ├─→ Learn about .env & settings.json
    └─→ Advanced configuration
    ↓
cli/README.md (technical)
    ├─→ API reference
    ├─→ Class documentation
    └─→ Code examples
    ↓
Done! Ready to use
```

## ✅ Validation System

All inputs are validated:

| Input Type | Validation |
|-----------|-----------|
| API Key | Min 5 chars, not empty |
| Token | Min 10 chars, not empty |
| Chat ID | Numeric (positive/negative) |
| Integer | Number, within range |
| URL | http/https format |
| Yes/No | y/n/yes/no |
| Choice | Valid option number |

## 🔧 Configuration Output

### Generated .env Example
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=xxxxx
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=123456789
DATABASE_URL=sqlite:///app/database/stock.db
DATABASE_TYPE=sqlite
AUTO_LEARNING=true
RISK_MODE=moderate
SCHEDULER_INTERVAL=15
MIN_CONFIDENCE_THRESHOLD=50
APP_PORT=8000
DEBUG=true
```

### Generated settings.json
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

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Setup wizard not showing | Run: `python cli/setup_wizard.py` |
| API connection failed | Check API key, internet, quota |
| Module import error | Run: `pip install -r requirements.txt` |
| Database error | Check permissions, disk space |
| Port already in use | Change port in config editor |
| Telegram not working | Verify token, check bot active |

More help: See SETUP_GUIDE.md Troubleshooting section

## 📚 Learning Resources

### CLI Libraries Used
- **Rich** - Terminal UI & formatting
- **Questionary** - Interactive prompts
- **Colorama** - Colored terminal text
- **Python-dotenv** - .env file handling

### Official Documentation
- [Rich Documentation](https://rich.readthedocs.io/)
- [Questionary Documentation](https://questionary.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python-dotenv Documentation](https://github.com/theskumar/python-dotenv)

## 🎓 Code Examples

### Using SetupWizard
```python
from cli.setup_wizard import SetupWizard

wizard = SetupWizard()
success = wizard.run()
if success:
    print("Setup completed!")
else:
    print("Setup cancelled")
```

### Using ConfigManager
```python
from cli.config import ConfigManager

manager = ConfigManager()
manager.run()  # Opens interactive config editor
```

### Using CLIManager
```python
from cli.manage import CLIManager

manager = CLIManager()
manager.run()  # Opens main menu
```

### Using Validators
```python
from cli.validators import Validator

validator = Validator()
is_valid, msg = validator.validate_api_key("your_api_key")
if is_valid:
    print("Valid!")
else:
    print(f"Error: {msg}")
```

### Using Helpers
```python
from cli.helpers import EnvManager, SettingsManager

# Manage .env
env = EnvManager()
data = env.load()
env.save({"KEY": "value"})

# Manage settings.json
settings = SettingsManager()
config = settings.load()
settings.save(config)
```

## 🏆 Best Practices

1. ✅ Always use `python setup.py` for initial setup
2. ✅ Test connections after configuration changes
3. ✅ Backup .env before major changes
4. ✅ Use `cli/config.py` for editing, not manual edits
5. ✅ Keep .env in .gitignore (already configured)
6. ✅ Read error messages carefully
7. ✅ Check logs for issues
8. ✅ Run `python test_cli.py` to verify system

## 🚀 Next Steps

After setup:

1. **View Application**
   - Open: http://localhost:8000
   - Try: API endpoints

2. **Configure Telegram Bot**
   - Optional but recommended
   - Get notifications via Telegram

3. **Run AI Training**
   - Use: `python cli/manage.py`
   - Select: Run AI Training

4. **Start Scheduler**
   - Use: `python cli/manage.py`
   - Monitors stock automatically

5. **Check Logs**
   - Use: `python cli/manage.py`
   - Select: View Logs

## 📞 Support

For issues:
1. Read: QUICKSTART.md
2. Check: SETUP_GUIDE.md
3. Review: cli/README.md
4. Test: python test_cli.py
5. Check: logs/ folder
6. Reset: python cli/config.py → Reset Configuration

## 📝 Files Summary

| File | Purpose | Updated |
|------|---------|---------|
| cli/setup_wizard.py | Main setup wizard | ✅ New |
| cli/config.py | Config editor | ✅ New |
| cli/manage.py | CLI manager | ✅ New |
| cli/validators.py | Input validation | ✅ New |
| cli/helpers.py | Helper utilities | ✅ New |
| setup.py | Setup entry point | ✅ New |
| config/settings.json | Config template | ✅ New |
| test_cli.py | Test suite | ✅ New |
| SETUP_GUIDE.md | Setup docs | ✅ New |
| QUICKSTART.md | Quick start | ✅ New |
| .env.example | .env template | ✅ New |
| requirements.txt | Dependencies | ✅ Updated |
| run.py | App entry | ✅ Updated |

## ✨ Features Implemented

- ✅ Interactive setup wizard (10 steps)
- ✅ Configuration manager
- ✅ CLI menu system
- ✅ Input validation
- ✅ Connection testing
- ✅ First run detection
- ✅ Auto .env generation
- ✅ Auto settings.json
- ✅ Directory creation
- ✅ Security features
- ✅ Error handling
- ✅ Clean UI (rich)
- ✅ Documentation
- ✅ Test suite

## 🎉 You're Ready!

Everything is set up and ready to use. Choose your next step:

```bash
# First time? Do setup
python setup.py

# Already setup? Run app
python run.py

# Want to configure?
python cli/config.py

# Need help?
cat QUICKSTART.md
```

---

**Version**: 1.0.0
**Status**: ✅ Complete & Production Ready
**Last Updated**: 2024
**Language**: Python 3.9+

**Enjoy your AI Stock Analyzer! 🚀**
