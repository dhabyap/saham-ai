"""Analisa-saham launcher — clean sys.path, bypass Hermes venv."""
import sys, os

# Strip Hermes paths
sys.path = [p for p in sys.path if 'hermes' not in p.replace('\\','/').lower()]

# chdir to project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Insert project root + Laragon site-packages
root = os.getcwd()
if root not in sys.path: sys.path.insert(0, root)

LARAGON_SP = r'C:\laragon\bin\python\python-3.10\Lib\site-packages'
if LARAGON_SP not in sys.path: sys.path.insert(0, LARAGON_SP)

# Vanilla import check
from app.main import app
import uvicorn
print(f"Starting Analisa-saham on http://localhost:8001")
uvicorn.run(app, host="127.0.0.1", port=8001)
