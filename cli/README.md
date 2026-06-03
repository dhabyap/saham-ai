# CLI System Documentation

Complete Interactive CLI Setup System untuk AI Stock Analyzer Indonesia.

## Overview

Sistem ini menyediakan:
- ✅ **Interactive Setup Wizard** - Konfigurasi awal yang mudah
- ✅ **Configuration Manager** - Edit config yang sudah ada
- ✅ **CLI Manager** - Menu utama untuk manage aplikasi
- ✅ **Validation System** - Input validation yang ketat
- ✅ **Connection Tester** - Test semua koneksi
- ✅ **Secure Input** - Hidden password/API key input

## Quick Start

### First Time Setup

```bash
# Method 1: Using setup.py (Recommended)
python setup.py

# Method 2: Direct run.py (Auto detect first run)
python run.py

# Method 3: Manual setup wizard
python cli/setup_wizard.py
```

### Main Operations

```bash
# Manage Configuration
python cli/config.py

# Open CLI Manager
python cli/manage.py

# Edit setup
python cli/setup_wizard.py
```

## Directory Structure

```
cli/
├── __init__.py          # Package initialization
├── setup_wizard.py      # Interactive setup wizard (Main)
├── config.py            # Configuration editor
├── manage.py            # CLI manager (Main menu)
├── validators.py        # Input validation functions
└── helpers.py           # Helper functions & utilities

config/
└── settings.json        # Non-sensitive configuration

logs/                   # Application logs
app/database/          # Database storage
```

## File Descriptions

### setup_wizard.py
**Main Setup Wizard**

Fitur:
- 10-step interactive wizard
- Auto .env generation
- Auto settings.json generation
- Folder creation
- Connection testing
- Input validation

Usage:
```bash
python cli/setup_wizard.py
```

### config.py
**Configuration Editor**

Fitur:
- View current config
- Edit individual settings
- Change API provider
- Update credentials
- Test connections
- Reset configuration

Usage:
```bash
python cli/config.py
```

### manage.py
**CLI Manager (Main Menu)**

Menu:
1. Start Web Server
2. Start Telegram Bot
3. Start Scheduler
4. Run AI Training
5. View Logs
6. Manage Configuration
7. Setup Wizard
8. View Application Info
9. Install Dependencies
10. Exit

Usage:
```bash
python cli/manage.py
```

### validators.py
**Input Validation**

Validates:
- API keys
- Tokens
- Chat IDs
- Integers
- URLs
- Yes/No inputs
- Choices

### helpers.py
**Helper Functions**

Classes:
- `EnvManager` - .env file operations
- `SettingsManager` - settings.json operations
- `FirstRunDetector` - Check first run

Functions:
- `print_*()` - Formatted output
- `create_directories()` - Create app folders
- `test_connection()` - Test API connectivity

## Configuration Flow

```
First Run Detected
        ↓
    Setup Wizard
        ↓
  Ask 10 Questions
        ↓
  Validate Inputs
        ↓
  Generate .env
        ↓
  Generate settings.json
        ↓
  Create Directories
        ↓
  Test Connections
        ↓
  Display Summary
```

## Input Questions (10 Steps)

| Step | Question | Options | Required |
|------|----------|---------|----------|
| 1 | AI Provider | OpenAI, Gemini, Ollama | ✓ |
| 2 | API Credentials | API Key + Model | ✓ |
| 3 | Telegram Bot | Yes/No | ✗ |
| 4 | Database | SQLite, PostgreSQL | ✓ |
| 5 | Auto Learning | Yes/No | ✓ |
| 6 | Risk Mode | Conservative/Moderate/Aggressive | ✓ |
| 7 | Monitor Interval | Minutes (1-1440) | ✓ |
| 8 | Ollama Fallback | Yes/No | ✓ |
| 9 | Additional Settings | Threshold, Port, Debug | ✓ |
| 10 | Review & Save | Confirm/Cancel | ✓ |

## Generated Configuration

### .env File
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

### settings.json
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

## Features

### 1. Interactive CLI Questions
- Modern questionary interface
- Input validation
- Error messages
- Help text

### 2. Auto .env Generation
- Create .env file automatically
- Set environment variables
- Use getpass for sensitive input

### 3. Validation System
- API key validation
- Chat ID validation (numeric)
- URL validation
- Integer range validation
- Yes/No validation

### 4. Secure Input
- Hidden password input using getpass
- API keys not displayed
- Show only last 5 chars in display

### 5. Connection Testing
- Test AI provider API
- Test Telegram Bot
- Test Database connection

### 6. First Run Detection
- Auto detect if .env missing
- Trigger setup wizard
- Skip if already configured

### 7. Configuration Editor
- View current settings
- Edit individual values
- Change AI provider
- Update credentials

### 8. CLI Menu System
- Start servers
- Start bots
- Run training
- View logs
- Manage config
- View app info

### 9. Auto Install Checker
- Check Python version
- Check pip packages
- Provide install instructions

### 10. Clean Terminal UI
- Rich formatting
- Colored output
- Progress bars
- Tables & panels

## Validation Rules

### API Key
- Min 5 characters
- Not empty
- No spaces allowed

### Token
- Min 10 characters
- Not empty

### Chat ID
- Must be numeric
- Can be negative (bot chat)
- Example: 123456789

### Integer
- Must be number
- Within specified range
- Example: 1-1440 for minutes

### URL
- Must start with http:// or https://
- Valid format

### Yes/No
- Input: y, n, yes, no
- Case insensitive

## Error Handling

Jika ada error:
1. Display error message yang jelas
2. Ask for input retry
3. Validate kembali
4. Continue jika valid

Contoh:
```
[red]✗ API key tidak boleh kosong[/red]
[cyan]Masukkan API Key:[/cyan]
> 
```

## Security Features

1. **Hidden Input**
   - API keys tidak di-echo ke terminal
   - Password input masked
   - Use `getpass` module

2. **File Permissions**
   - .env not readable by others
   - Sensitive data encrypted (future)

3. **Validation**
   - Strict input validation
   - Type checking
   - Format checking

4. **Safe Storage**
   - Sensitive: .env (add to .gitignore)
   - Non-sensitive: settings.json

## Usage Examples

### Example 1: Initial Setup
```bash
$ python setup.py

================================================
  AI STOCK ANALYZER - SETUP
================================================

Installing Python Dependencies...
✓ Dependencies installed successfully

[Setup Wizard Starts]
[1/10] Pilih AI Provider:
...
```

### Example 2: Edit Configuration
```bash
$ python cli/config.py

================================
AI STOCK ANALYZER - CONFIG EDITOR
================================

Pilih aksi:
1. View Current Config
2. Edit AI Provider
...
```

### Example 3: CLI Manager
```bash
$ python cli/manage.py

================================
AI STOCK ANALYZER MANAGER
================================

Pilih opsi:
1. Start Web Server
2. Start Telegram Bot
...
```

### Example 4: Test Connections
```bash
$ python cli/config.py
[Select: Test Connections]

Testing Gemini API...
✓ Gemini API connection OK

Testing Telegram Bot...
✓ Telegram Bot connection OK

Testing Database...
✓ SQLite database path OK
```

## Troubleshooting

### Setup Wizard Not Showing
- Ensure .env doesn't exist
- Run: `python cli/setup_wizard.py` manually

### API Connection Failed
- Verify API key is correct
- Check internet connection
- Check API quota/limits

### Validation Error
- Read error message carefully
- Re-enter value with correct format
- Example for Chat ID: Use numeric value

### File Permission Error
- Check folder permissions
- Ensure write access to project folder
- Run with appropriate permissions

## Performance

- Setup wizard: ~2 seconds
- Config edit: Instant
- Connection test: 1-5 seconds
- Menu navigation: Instant

## Dependencies

```
rich>=13.7.0         # Terminal UI
questionary>=2.2.1   # Interactive questions
colorama>=0.4.6      # Colored output
python-dotenv>=1.0.1 # .env handling
```

Auto-installed via `python setup.py`

## Best Practices

1. **Always use setup.py for first setup**
   - Installs dependencies first
   - Ensures all packages available

2. **Test connections after setup**
   - Verify API keys work
   - Check Telegram bot active
   - Confirm database accessible

3. **Backup configuration**
   - Copy .env before changes
   - Store credentials securely
   - Document changes

4. **Use config editor for changes**
   - Don't manually edit .env
   - Use cli/config.py for edits
   - Test after changes

## Advanced Features (Future)

- [ ] Multi-profile configuration
- [ ] Config encryption
- [ ] Config backup/restore
- [ ] Remote config sync
- [ ] Configuration import/export
- [ ] Environment-specific configs (dev/staging/prod)

## API Reference

### SetupWizard Class

```python
from cli.setup_wizard import SetupWizard

wizard = SetupWizard()
success = wizard.run()  # Returns True if successful
```

### ConfigManager Class

```python
from cli.config import ConfigManager

manager = ConfigManager()
manager.run()  # Open interactive config editor
```

### CLIManager Class

```python
from cli.manage import CLIManager

manager = CLIManager()
manager.run()  # Open main menu
```

### Validators

```python
from cli.validators import Validator

validator = Validator()
is_valid, msg = validator.validate_api_key("key_value")
is_valid, msg = validator.validate_chat_id("123456789")
is_valid, msg = validator.validate_integer("15", 1, 1440)
```

### Helpers

```python
from cli.helpers import (
    EnvManager, SettingsManager, FirstRunDetector,
    print_success, print_error, print_info,
    test_connection, create_directories
)

env_manager = EnvManager()
env_data = env_manager.load()
env_manager.save(data)

settings_manager = SettingsManager()
settings = settings_manager.load()
settings_manager.save(data)

detector = FirstRunDetector()
if detector.is_first_run():
    print("First run detected!")
```

## Support

For issues:
1. Check SETUP_GUIDE.md for detailed guide
2. Review error message carefully
3. Check logs/ for application logs
4. Test connections in config editor
5. Reset configuration if corrupted

---

**Version**: 1.0.0
**Status**: Complete & Production Ready
**Language**: Python 3.9+
**Interactive UI**: Rich + Questionary + Colorama

## Credits

Built with:
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal UI
- [Questionary](https://github.com/tom-ki/questionary) - Interactive CLI
- [Colorama](https://github.com/tartley/colorama) - Color terminal text
