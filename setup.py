#!/usr/bin/env python3
"""
AI Stock Analyzer Setup Script
Initial setup and dependency installation
"""

import sys
import subprocess
from pathlib import Path

def install_dependencies():
    """Install required dependencies"""
    print("=" * 50)
    print("  Installing Python Dependencies...")
    print("=" * 50)
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("\n✓ Dependencies installed successfully\n")
        return True
    except subprocess.CalledProcessError:
        print("\n✗ Error installing dependencies\n")
        return False


def run_setup_wizard():
    """Run the setup wizard"""
    try:
        from cli.setup_wizard import SetupWizard
        wizard = SetupWizard()
        return wizard.run()
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install dependencies first")
        return False


def main():
    """Main setup entry point"""
    print("\n")
    print("=" * 50)
    print("  AI STOCK ANALYZER - SETUP")
    print("=" * 50)
    print()

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Run setup wizard
    if not run_setup_wizard():
        print("Setup cancelled or failed")
        sys.exit(1)

    print("\n✓ Setup complete! You can now run:")
    print("\n  python run.py          # Start web server")
    print("  python cli/manage.py   # Open CLI manager")
    print()


if __name__ == "__main__":
    main()
