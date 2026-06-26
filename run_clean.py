"""Clean launcher for analisa-saham — avoids Hermes venv path pollution."""
import sys
sys.path = [p for p in sys.path if 'hermes' not in p.replace('\\', '/').lower()]

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Force Laragon site-packages
LARAGON = r'C:\laragon\bin\python\python-3.10'
sp = os.path.join(LARAGON, 'Lib', 'site-packages')
if sp not in sys.path:
    sys.path.insert(0, sp)

import uvicorn
from app.main import app
from app.config import Config

print("=" * 50)
print("  AI STOCK ANALYZER INDONESIA")
print("=" * 50)
print(f"\n  Dashboard: http://localhost:{Config.APP_PORT}")
print(f"  API:       http://localhost:{Config.APP_PORT}/api/health\n")

uvicorn.run(
    app,
    host=Config.APP_HOST,
    port=Config.APP_PORT,
    reload=False,
)
