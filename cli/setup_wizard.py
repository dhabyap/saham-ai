"""
Interactive CLI Setup Wizard for AI Stock Analyzer
Guides user through initial configuration
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
import getpass

from .validators import Validator
from .helpers import (
    EnvManager, SettingsManager, FirstRunDetector, 
    print_header, print_step, print_success, print_error, 
    print_info, create_directories, test_connection
)

console = Console()
validator = Validator()


class SetupWizard:
    """Interactive setup wizard for initial configuration"""

    def __init__(self):
        self.env_manager = EnvManager()
        self.settings_manager = SettingsManager()
        self.validator = Validator()
        self.config: Dict[str, Any] = {}
        self.settings: Dict[str, Any] = {}

    def run(self) -> bool:
        """Run the complete setup wizard"""
        print_header("AI STOCK ANALYZER SETUP WIZARD")
        
        # Welcome message
        console.print(Panel(
            """[bold cyan]Selamat datang di Setup Wizard![/bold cyan]

Wizard ini akan membantu Anda mengatur aplikasi dengan mudah.
Semua konfigurasi akan disimpan di file [bold].env[/bold] dan [bold]config/settings.json[/bold]

Anda bisa menjalankan ulang wizard ini kapan saja dengan perintah:
[bold cyan]python cli/setup_wizard.py[/bold cyan]""",
            title="Info",
            expand=False
        ))

        console.print("\n[cyan]Tekan Enter untuk memulai...[/cyan]")
        input()

        try:
            # Check system requirements
            if not self._check_requirements():
                return False

            # Wizard steps
            if not self._step_ai_provider():
                return False
            
            if not self._step_ai_credentials():
                return False
            
            if not self._step_telegram():
                return False
            
            if not self._step_database():
                return False
            
            if not self._step_learning_settings():
                return False
            
            if not self._step_risk_mode():
                return False
            
            if not self._step_monitoring():
                return False
            
            if not self._step_ollama_fallback():
                return False
            
            if not self._step_additional_settings():
                return False
            
            # Review and save
            if not self._review_and_save():
                return False
            
            # Test connections
            self._test_connections()
            
            # Create directories
            self._create_required_directories()
            
            print_header("SETUP SELESAI", 50)
            console.print(Panel(
                """[bold green]✓ Konfigurasi berhasil disimpan![/bold green]

File yang dibuat:
• [cyan].env[/cyan] - Konfigurasi sensitif
• [cyan]config/settings.json[/cyan] - Konfigurasi umum
• [cyan]logs/[/cyan] - Folder logs
• [cyan]app/database/[/cyan] - Folder database

Jalankan aplikasi dengan:
[bold cyan]python run.py[/bold cyan]

Atau gunakan CLI Manager:
[bold cyan]python cli/manage.py[/bold cyan]""",
                title="Selesai",
                expand=False
            ))
            
            return True

        except KeyboardInterrupt:
            print_error("Setup dibatalkan oleh user")
            return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def _check_requirements(self) -> bool:
        """Check system requirements"""
        print_step(0, 10, "Checking system requirements...")
        
        required_packages = [
            ('python', 'Python', '3.9'),
            ('requests', 'Requests library', '2.0'),
        ]

        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Checking...", total=len(required_packages))
            
            for check_name, display_name, min_version in required_packages:
                try:
                    if check_name == 'python':
                        import platform
                        version = platform.python_version()
                        print_success(f"Python {version}")
                    else:
                        __import__(check_name)
                        print_success(f"{display_name} installed")
                    progress.update(task, advance=1)
                except ImportError:
                    print_error(f"{display_name} not found")
                    print_info(f"Install with: pip install {check_name}")
                    progress.update(task, advance=1)

        return True

    def _step_ai_provider(self) -> bool:
        """Step 1: Choose AI Provider"""
        step = 1
        total = 10
        
        providers = [
            "OpenAI",
            "Gemini (Google)",
            "Ollama (Local)",
        ]

        print_step(step, total, "Pilih AI Provider:")
        console.print("\nOpsi:")
        for i, provider in enumerate(providers, 1):
            console.print(f"  {i}. {provider}")

        while True:
            choice = questionary.text(
                "\nInput (1-3):",
                validate=lambda x: self.validator.validate_choice(x, providers)[0]
            ).ask()

            if choice:
                idx = int(choice) - 1
                self.config['AI_PROVIDER'] = providers[idx].lower().split()[0]
                self.settings['ai_provider'] = self.config['AI_PROVIDER']
                print_success(f"Dipilih: {providers[idx]}")
                return True

    def _step_ai_credentials(self) -> bool:
        """Step 2: Get AI Provider credentials"""
        step = 2
        total = 10
        provider = self.config.get('AI_PROVIDER', 'openai')

        print_step(step, total, f"Setup {provider.upper()} Credentials")

        if provider.lower() == 'openai':
            while True:
                api_key = questionary.password(
                    "Masukkan OpenAI API Key:",
                    validate=lambda x: self.validator.validate_api_key(x)[0]
                ).ask()

                if api_key:
                    self.config['OPENAI_API_KEY'] = api_key
                    print_success("OpenAI API Key disimpan")

                    # Ask for model
                    model = questionary.text(
                        "OpenAI Model (default: gpt-4-turbo):",
                        default="gpt-4-turbo"
                    ).ask()
                    self.config['OPENAI_MODEL'] = model or "gpt-4-turbo"
                    return True

        elif provider.lower() == 'gemini':
            while True:
                api_key = questionary.password(
                    "Masukkan Gemini API Key:",
                    validate=lambda x: self.validator.validate_api_key(x)[0]
                ).ask()

                if api_key:
                    self.config['GEMINI_API_KEY'] = api_key
                    print_success("Gemini API Key disimpan")

                    # Ask for model
                    model = questionary.text(
                        "Gemini Model (default: gemini-2.0-flash):",
                        default="gemini-2.0-flash"
                    ).ask()
                    self.config['GEMINI_MODEL'] = model or "gemini-2.0-flash"
                    return True

        elif provider.lower() == 'ollama':
            while True:
                url = questionary.text(
                    "Ollama Base URL (default: http://localhost:11434):",
                    default="http://localhost:11434",
                    validate=lambda x: self.validator.validate_url(x)[0]
                ).ask()

                if url:
                    self.config['OLLAMA_BASE_URL'] = url
                    print_success("Ollama URL disimpan")

                    model = questionary.text(
                        "Ollama Model (default: llama3):",
                        default="llama3"
                    ).ask()
                    self.config['OLLAMA_MODEL'] = model or "llama3"
                    return True

    def _step_telegram(self) -> bool:
        """Step 3: Configure Telegram Bot"""
        step = 3
        total = 10
        
        print_step(step, total, "Gunakan Telegram Bot?")

        use_telegram = questionary.confirm(
            "Setup Telegram Bot?",
            default=True
        ).ask()

        if use_telegram:
            while True:
                bot_token = questionary.password(
                    "Masukkan TELEGRAM BOT TOKEN:",
                    validate=lambda x: self.validator.validate_token(x)[0]
                ).ask()

                if bot_token:
                    self.config['TELEGRAM_BOT_TOKEN'] = bot_token
                    print_success("Telegram Bot Token disimpan")
                    break

            while True:
                chat_id = questionary.text(
                    "Masukkan TELEGRAM CHAT ID:",
                    validate=lambda x: self.validator.validate_chat_id(x)[0]
                ).ask()

                if chat_id:
                    self.config['TELEGRAM_CHAT_ID'] = chat_id
                    print_success("Telegram Chat ID disimpan")
                    return True
        else:
            self.config['TELEGRAM_BOT_TOKEN'] = ""
            self.config['TELEGRAM_CHAT_ID'] = ""
            print_info("Telegram Bot dilewatkan")
            return True

    def _step_database(self) -> bool:
        """Step 4: Choose Database"""
        step = 4
        total = 10
        
        databases = ["SQLite", "PostgreSQL"]

        print_step(step, total, "Pilih Database:")
        console.print("\nOpsi:")
        for i, db in enumerate(databases, 1):
            console.print(f"  {i}. {db}")

        while True:
            choice = questionary.text(
                "\nInput (1-2):",
                validate=lambda x: self.validator.validate_choice(x, databases)[0]
            ).ask()

            if choice:
                idx = int(choice) - 1
                db_type = databases[idx]
                self.config['DATABASE_TYPE'] = db_type.lower()
                
                if db_type.lower() == 'sqlite':
                    db_path = questionary.text(
                        "Database path (default: app/database/stock.db):",
                        default="app/database/stock.db"
                    ).ask()
                    db_url = f"sqlite:///{db_path}"
                else:
                    # PostgreSQL
                    host = questionary.text(
                        "PostgreSQL Host (default: localhost):",
                        default="localhost"
                    ).ask()
                    port = questionary.text(
                        "PostgreSQL Port (default: 5432):",
                        default="5432"
                    ).ask()
                    user = questionary.text("PostgreSQL User:").ask()
                    password = questionary.password("PostgreSQL Password:").ask()
                    db_name = questionary.text("Database Name:").ask()
                    
                    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

                self.config['DATABASE_URL'] = db_url
                print_success(f"Database: {db_type}")
                return True

    def _step_learning_settings(self) -> bool:
        """Step 5: Enable Auto Learning"""
        step = 5
        total = 10
        
        print_step(step, total, "Enable Auto Learning?")

        auto_learning = questionary.confirm(
            "Enable Auto Learning?",
            default=True
        ).ask()

        self.config['AUTO_LEARNING'] = "true" if auto_learning else "false"
        self.settings['auto_learning'] = auto_learning
        print_success(f"Auto Learning: {'Enabled' if auto_learning else 'Disabled'}")
        return True

    def _step_risk_mode(self) -> bool:
        """Step 6: Choose Risk Mode"""
        step = 6
        total = 10
        
        risk_modes = ["Conservative", "Moderate", "Aggressive"]

        print_step(step, total, "Pilih Risk Mode:")
        console.print("\nOpsi:")
        for i, mode in enumerate(risk_modes, 1):
            console.print(f"  {i}. {mode}")

        while True:
            choice = questionary.text(
                "\nInput (1-3):",
                validate=lambda x: self.validator.validate_choice(x, risk_modes)[0]
            ).ask()

            if choice:
                idx = int(choice) - 1
                risk_mode = risk_modes[idx].lower()
                self.config['RISK_MODE'] = risk_mode
                self.config['DEFAULT_RISK_LEVEL'] = risk_mode
                self.settings['risk_mode'] = risk_mode
                print_success(f"Risk Mode: {risk_modes[idx]}")
                return True

    def _step_monitoring(self) -> bool:
        """Step 7: Set Monitoring Interval"""
        step = 7
        total = 10
        
        print_step(step, total, "Interval Monitoring (minutes)")

        while True:
            interval = questionary.text(
                "Interval (default: 15, min: 1, max: 1440):",
                default="15",
                validate=lambda x: self.validator.validate_integer(x, 1, 1440)[0]
            ).ask()

            if interval:
                self.config['MONITOR_INTERVAL'] = int(interval)
                self.config['SCHEDULER_INTERVAL'] = int(interval)
                self.settings['monitor_interval'] = int(interval)
                print_success(f"Monitoring Interval: {interval} menit")
                return True

    def _step_ollama_fallback(self) -> bool:
        """Step 8: Enable Ollama Local Fallback"""
        step = 8
        total = 10
        
        print_step(step, total, "Enable Local AI Fallback (Ollama)?")

        enable_ollama = questionary.confirm(
            "Enable Ollama Local Fallback?",
            default=False
        ).ask()

        if enable_ollama:
            ollama_url = questionary.text(
                "Ollama URL (default: http://localhost:11434):",
                default="http://localhost:11434",
                validate=lambda x: self.validator.validate_url(x)[0]
            ).ask()

            if ollama_url:
                self.config['OLLAMA_ENABLED'] = "true"
                self.config['OLLAMA_BASE_URL'] = ollama_url
                self.config['OLLAMA_MODEL'] = "llama3"
                self.settings['ollama_enabled'] = True
                print_success("Ollama Fallback Enabled")
                return True
        else:
            self.config['OLLAMA_ENABLED'] = "false"
            self.settings['ollama_enabled'] = False
            print_info("Ollama Fallback Disabled")
            return True

    def _step_additional_settings(self) -> bool:
        """Step 9: Additional Settings"""
        step = 9
        total = 10
        
        print_step(step, total, "Konfigurasi Tambahan")

        # Min confidence threshold
        threshold = questionary.text(
            "Min Confidence Threshold (default: 50, range: 0-100):",
            default="50",
            validate=lambda x: self.validator.validate_integer(x, 0, 100)[0]
        ).ask()

        if threshold:
            self.config['MIN_CONFIDENCE_THRESHOLD'] = int(threshold)
            self.settings['min_confidence_threshold'] = int(threshold)

        # App port
        port = questionary.text(
            "App Port (default: 8000):",
            default="8000",
            validate=lambda x: self.validator.validate_integer(x, 1024, 65535)[0]
        ).ask()

        if port:
            self.config['APP_PORT'] = int(port)

        # Debug mode
        debug = questionary.confirm(
            "Enable Debug Mode?",
            default=True
        ).ask()

        self.config['DEBUG'] = "true" if debug else "false"

        print_success("Konfigurasi tambahan disimpan")
        return True

    def _review_and_save(self) -> bool:
        """Step 10: Review and Save Configuration"""
        step = 10
        total = 10
        
        print_step(step, total, "Review Konfigurasi")

        console.print("\n[cyan]Konfigurasi yang akan disimpan:[/cyan]")
        console.print()

        # Show config (with hidden sensitive values)
        config_display = {}
        for key, value in self.config.items():
            if 'key' in key.lower() or 'token' in key.lower():
                config_display[key] = f"{'*' * (len(str(value)) - 5)}...{str(value)[-5:]}"
            else:
                config_display[key] = value

        from .helpers import print_table
        print_table("Configuration", config_display)

        # Confirm save
        confirm = questionary.confirm(
            "\nSimpan konfigurasi ini?",
            default=True
        ).ask()

        if confirm:
            # Save .env
            if not self.env_manager.save(self.config):
                print_error("Gagal menyimpan .env")
                return False
            
            # Save settings.json
            self.settings = {**self.settings_manager.get_default_settings(), **self.settings}
            if not self.settings_manager.save(self.settings):
                print_error("Gagal menyimpan settings.json")
                return False

            print_success("Konfigurasi berhasil disimpan")
            return True
        else:
            print_info("Setup dibatalkan")
            return False

    def _test_connections(self):
        """Test all connections"""
        print_step(1, 3, "Testing Connections")
        console.print()

        # Test AI Provider
        provider = self.config.get('AI_PROVIDER', 'openai')
        api_key = None

        if provider == 'openai':
            api_key = self.config.get('OPENAI_API_KEY')
        elif provider == 'gemini':
            api_key = self.config.get('GEMINI_API_KEY')
        elif provider == 'ollama':
            api_key = self.config.get('OLLAMA_BASE_URL')

        if api_key:
            if test_connection(provider, api_key):
                print_success(f"{provider.upper()} API connection OK")
            else:
                print_error(f"{provider.upper()} API connection failed")

        # Test Telegram Bot
        if self.config.get('TELEGRAM_BOT_TOKEN'):
            try:
                from telegram import Bot
                bot = Bot(token=self.config['TELEGRAM_BOT_TOKEN'])
                bot.get_me()
                print_success("Telegram Bot connection OK")
            except Exception as e:
                print_error(f"Telegram Bot connection failed: {e}")

    def _create_required_directories(self):
        """Create required application directories"""
        dirs = [
            'app/database',
            'app/static/charts',
            'config',
            'logs',
        ]
        create_directories(dirs)
        print_success("Direktori aplikasi berhasil dibuat")


def main():
    """Main entry point"""
    wizard = SetupWizard()
    success = wizard.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
