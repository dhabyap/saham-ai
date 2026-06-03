# QUICK START GUIDE - CLI Setup System

Panduan cepat untuk mulai menggunakan AI Stock Analyzer dengan Interactive CLI Setup.

## Installation & Setup (5 menit)

### Step 1: Clone/Open Project
```bash
cd d:\Latihan\Saham\analisa-saham
```

### Step 2: Install Dependencies & Setup
```bash
# Method A: Recommended (One command)
python setup.py

# Method B: Direct
python run.py

# Method C: Manual
python cli/setup_wizard.py
```

### Step 3: Answer Questions
Sistem akan bertanya 10 pertanyaan:

1. **AI Provider** → Pilih: Gemini, OpenAI, atau Ollama
2. **API Key** → Paste API key dari provider
3. **Telegram Bot** → Setup notifikasi via Telegram (optional)
4. **Database** → SQLite (default) atau PostgreSQL
5. **Auto Learning** → Aktifkan AI learning otomatis
6. **Risk Mode** → Conservative, Moderate, atau Aggressive
7. **Monitor Interval** → Berapa menit check stock (default: 15)
8. **Ollama Fallback** → Local AI jika API down (optional)
9. **Additional** → Confidence threshold, port, debug mode
10. **Confirm** → Review & save konfigurasi

### Step 4: Done!
System akan auto create:
- ✅ `.env` file
- ✅ `config/settings.json`
- ✅ Required folders
- ✅ Test all connections

## Usage Commands

### Run Web Server (First Run Auto Setup)
```bash
python run.py
# Dashboard: http://localhost:8000
```

### Open CLI Manager
```bash
python cli/manage.py
# Menu untuk manage aplikasi
```

### Edit Configuration
```bash
python cli/config.py
# Edit settings, change API key, etc
```

### Manual Setup Wizard
```bash
python cli/setup_wizard.py
# Re-run setup jika ada error
```

## Common Tasks

### 1. Setup Gemini API
```
1. Run: python setup.py
2. Select: 2 (Gemini)
3. Get API Key from: https://aistudio.google.com/app/apikey
4. Paste key saat diminta
5. Done!
```

### 2. Setup Telegram Bot
```
1. Create bot via @BotFather di Telegram
2. Copy token
3. Get your Chat ID: https://t.me/username_to_id_bot
4. Run: python cli/config.py
5. Select: Edit Telegram Settings
6. Paste token & chat ID
```

### 3. Use PostgreSQL Instead of SQLite
```
1. Run: python cli/config.py
2. Select: Edit Database
3. Select: PostgreSQL
4. Enter: Host, Port, Username, Password, Database Name
5. Done!
```

### 4. Change Risk Mode
```
1. Run: python cli/config.py
2. Select: Edit Risk Mode
3. Choose: Conservative/Moderate/Aggressive
4. Done!
```

### 5. Test All Connections
```
1. Run: python cli/config.py
2. Select: Test Connections
3. See results: [OK] or [FAILED]
```

## Configuration Files

### .env (Auto Created)
File ini menyimpan API keys dan config sensitif.
- **DON'T COMMIT** ke git!
- **DON'T SHARE** ke orang lain!
- Backup: `cp .env .env.backup`

### config/settings.json (Auto Created)
File ini menyimpan config non-sensitif.
- Safe untuk di-version control
- Edit via CLI Manager

## First Run Checklist

- [ ] Run setup.py
- [ ] Choose AI provider
- [ ] Enter API key
- [ ] Test connection [OK]
- [ ] Setup database
- [ ] Answer remaining questions
- [ ] Review configuration
- [ ] Confirm save
- [ ] Wait for directory creation
- [ ] Ready to use!

## Project Structure After Setup

```
analisa-saham/
├── .env              ← Auto created (KEEP SECRET!)
├── app/
│   ├── config.py
│   ├── database/
│   │   └── stock.db  ← Auto created
│   ├── static/
│   │   └── charts/   ← Auto created
│   └── ...
├── cli/              ← New CLI system
│   ├── setup_wizard.py
│   ├── config.py
│   ├── manage.py
│   └── ...
├── config/           ← New config folder
│   └── settings.json ← Auto created
├── logs/             ← Auto created
│   └── *.log
├── requirements.txt  ← Updated
├── run.py            ← Updated (auto setup)
├── setup.py          ← New
└── SETUP_GUIDE.md    ← Documentation
```

## Troubleshooting

### Q: Setup wizard not showing?
**A**: Run manual: `python cli/setup_wizard.py`

### Q: "API connection failed"?
**A**: Check API key correct, test internet, check quota

### Q: "Telegram Bot failed"?
**A**: Verify token from @BotFather, check bot active

### Q: Want to change configuration?
**A**: Run: `python cli/config.py`

### Q: Want to reset everything?
**A**: 
```bash
python cli/config.py
# Select: Reset Configuration
```

### Q: Database error?
**A**: Check folder permissions, disk space, then retry

### Q: Port 8000 already in use?
**A**: 
```bash
python cli/config.py
# Select: Edit Additional Settings
# Change: App Port
```

## Demo Flow

```
$ python setup.py

================================================
  AI STOCK ANALYZER - SETUP
================================================

Installing Python Dependencies...
✓ Dependencies installed successfully

==================================================
 AI STOCK ANALYZER SETUP WIZARD
==================================================

[1/10] Pilih AI Provider:
1. OpenAI
2. Gemini (Google)
3. Ollama (Local)

Input: 2

[2/10] Masukkan GEMINI API KEY:
> YOUR_API_KEY_HERE

[3/10] Gunakan Telegram Bot?
(y/n)
> y

[4/10] Masukkan TELEGRAM BOT TOKEN:
> YOUR_BOT_TOKEN

[5/10] Masukkan TELEGRAM CHAT ID:
> 123456789

... (more questions)

[10/10] Review Konfigurasi

[cyan]Konfigurasi yang akan disimpan:[/cyan]

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Setting            ┃ Value     ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ AI_PROVIDER        │ gemini    │
│ GEMINI_API_KEY     │ ****...** │
│ TELEGRAM_BOT_TOKEN │ ****...** │
│ DATABASE_TYPE      │ sqlite    │
│ RISK_MODE          │ moderate  │
└────────────────────┴───────────┘

Simpan konfigurasi ini? [Y/n]: y

[OK]    .env file saved
[OK]    settings.json saved
[OK]    Directories created

Testing Connections...
✓ Gemini API connection OK
✓ Telegram Bot connection OK
✓ SQLite database path OK

==================================================
SETUP COMPLETE
==================================================

File yang dibuat:
• .env - Konfigurasi sensitif
• config/settings.json - Konfigurasi umum
• logs/ - Folder logs
• app/database/ - Folder database

Jalankan aplikasi dengan:
  python run.py

Atau gunakan CLI Manager:
  python cli/manage.py

```

## Next Steps

After setup, you can:

1. **Start Web Server**
   ```bash
   python run.py
   # Open: http://localhost:8000
   ```

2. **Open CLI Manager**
   ```bash
   python cli/manage.py
   # Manage all aspects of app
   ```

3. **Edit Configuration**
   ```bash
   python cli/config.py
   # Change any settings anytime
   ```

4. **Start Telegram Bot**
   ```bash
   python -m app.telegram.bot
   # Get notifications via Telegram
   ```

5. **Run AI Training**
   ```bash
   python -m app.ai.training_engine
   # Train AI model
   ```

## Resources

- 📖 **Full Guide**: See `SETUP_GUIDE.md`
- 🔧 **CLI Docs**: See `cli/README.md`
- 📝 **API Docs**: http://localhost:8000/docs (after running)
- 🎥 **Demo**: Run `python setup.py` to see interactive demo

## Support

If you encounter issues:

1. **Check logs**
   ```bash
   python cli/manage.py
   # Select: View Logs
   ```

2. **Test connections**
   ```bash
   python cli/config.py
   # Select: Test Connections
   ```

3. **Reset & retry**
   ```bash
   python cli/config.py
   # Select: Reset Configuration
   # Then run: python setup.py
   ```

4. **Read documentation**
   - `SETUP_GUIDE.md` - Complete setup guide
   - `cli/README.md` - CLI system documentation
   - `README.md` - Project overview

## Tips & Tricks

1. **Save your .env backup**
   ```bash
   cp .env .env.backup
   ```

2. **Switch between multiple configs**
   ```bash
   # Keep multiple configs
   cp .env .env.development
   cp .env .env.production
   # Switch with cli/config.py
   ```

3. **Test API before full setup**
   - Run setup wizard
   - At review step, just test connection
   - Go back if failed

4. **Use SQLite for development**
   - Faster, no setup needed
   - Good for testing

5. **Use PostgreSQL for production**
   - Better performance
   - Support concurrent users
   - Easier backups

## Learning Resources

- **Rich Library**: https://rich.readthedocs.io/
- **Questionary**: https://questionary.readthedocs.io/
- **Python dotenv**: https://github.com/theskumar/python-dotenv
- **FastAPI**: https://fastapi.tiangolo.com/

---

**Version**: 1.0.0
**Last Updated**: 2024
**Status**: Ready to Use ✅

🎉 **Enjoy your AI Stock Analyzer!** 🎉
