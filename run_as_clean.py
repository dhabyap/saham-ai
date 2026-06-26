"""Analisa-saham launcher — clean Hermes-free path."""
import sys, os
# Strip Hermes venv paths
sys.path = [p for p in sys.path if 'hermes' not in p.replace(os.sep, '/').lower()]
os.chdir(os.path.dirname(os.path.abspath(__file__)))
root = os.getcwd()
if root not in sys.path: sys.path.insert(0, root)
# Add Laragon site-packages
LARAGON_SP = r'C:\laragon\bin\python\python-3.10\Lib\site-packages'
if LARAGON_SP not in sys.path: sys.path.insert(0, LARAGON_SP)

import uvicorn
from app.main import app
print("Starting Analisa-Saham on http://localhost:8001")
sys.stdout.flush()
uvicorn.run(app, host="0.0.0.0", port=8001, reload=False, log_level="info")
