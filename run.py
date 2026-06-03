#!/usr/bin/env python3
"""
AI Stock Analyzer Indonesia
Main entry point to run the application.
"""

import sys
from pathlib import Path

# Check if configuration exists
if not Path(".env").exists():
    print("=" * 60)
    print("  FIRST RUN DETECTED")
    print("=" * 60)
    print("\nBelum ada file konfigurasi (.env)")
    print("\nAkan menjalankan Setup Wizard...\n")
    
    try:
        from cli.setup_wizard import SetupWizard
        wizard = SetupWizard()
        success = wizard.run()
        
        if not success:
            print("\nSetup dibatalkan. Jalankan kembali dengan: python run.py")
            sys.exit(1)
    except ImportError as e:
        print(f"Error: {e}")
        print("Jalankan setup manual dengan: python setup.py")
        sys.exit(1)

import uvicorn
from app.config import Config

if __name__ == "__main__":
    print("=" * 50)
    print("  AI STOCK ANALYZER INDONESIA")
    print("  IDX Stock Analysis with AI")
    print("=" * 50)
    print(f"\n  Dashboard: http://localhost:{Config.APP_PORT}")
    print(f"  API Docs:  http://localhost:{Config.APP_PORT}/docs")
    print(f"  API:       http://localhost:{Config.APP_PORT}/api/health\n")

    uvicorn.run(
        "app.main:app",
        host=Config.APP_HOST,
        port=Config.APP_PORT,
        reload=Config.DEBUG,
    )
