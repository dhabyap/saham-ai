#!/usr/bin/env python3
"""
AI Stock Analyzer Indonesia
Main entry point to run the application.
"""

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
