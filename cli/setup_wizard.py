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

# Monkey-patch questionary to raise KeyboardInterrupt on Ctrl+C/Escape
_original_ask = questionary.Question.ask
def _safe_ask(self):
    result = _original_ask(self)
    if result is None:
        raise KeyboardInterrupt()
    return result
questionary.Question.ask = _safe_ask

console = Console()
validator = Validator()


class SetupWizard:
    """Interactive setup wizard for initial configuration"""

    def __init__(self):
        self.env_manager = EnvManager()
        self.settings_manager = SettingsManager()
        self.validator = Validator()
        self.existing_env = self.env_manager.load()
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
        """Step 1: 9Router Provider (fixed)"""
        step = 1
        total = 10
        
        print_step(step, total, "AI Provider")
        
        # 9Router is the only provider
        self.config['AI_PROVIDER'] = "9router"
        self.settings['ai_provider'] = "9router"
        
        console.print("\n[cyan]Provider yang digunakan:[/cyan]")
        console.print("  1. 9Router (Fixed)")
        console.print("\n[cyan]Provider dipilih: 9Router[/cyan]")
        return True

    def _step_ai_credentials(self) -> bool:
        """Step 2: Setup 9Router credentials"""
        step = 2
        total = 10

        print_step(step, total, "Setup 9Router Credentials")

        existing_url = self.existing_env.get('NINE_ROUTER_BASE_URL', '')
        default_url = existing_url or 'http://localhost:20128/v1'
        url = questionary.text(
            "9Router Base URL:",
            default=default_url,
            validate=lambda x: self.validator.validate_url(x)[0]
        ).ask()
        self.config['NINE_ROUTER_BASE_URL'] = url or default_url

        model = questionary.text(
            "9Router Model:",
            default=self.existing_env.get('NINE_ROUTER_MODEL', 'test')
        ).ask()
        self.config['NINE_ROUTER_MODEL'] = model or self.existing_env.get('NINE_ROUTER_MODEL', 'test')

        existing_key = self.existing_env.get('NINE_ROUTER_API_KEY', '')
        default_key = existing_key or 'sk-9router-free'
        api_key = questionary.text(
            "9Router API Key:",
            default=default_key,
        ).ask()
        self.config['NINE_ROUTER_API_KEY'] = api_key or default_key

        print_success("9Router credentials disimpan")
        return True

    def _step_telegram(self) -> bool:
        """Step 3: Configure Telegram Bot"""
        step = 3
        total = 10
        
        has_existing = bool(self.existing_env.get('TELEGRAM_BOT_TOKEN'))
        print_step(step, total, "Gunakan Telegram Bot?")

        if has_existing:
            print_info(f"Telegram Bot sudah terisi ({self.existing_env.get('TELEGRAM_BOT_TOKEN', '')[:8]}...)")
            use_telegram = questionary.confirm(
                "Update Telegram settings?",
                default=False
            ).ask()
            if not use_telegram:
                self.config['TELEGRAM_BOT_TOKEN'] = self.existing_env['TELEGRAM_BOT_TOKEN']
                self.config['TELEGRAM_CHAT_ID'] = self.existing_env.get('TELEGRAM_CHAT_ID', '')
                print_info("Telegram settings tidak diubah")
                return True

        use_telegram = questionary.confirm(
            "Setup Telegram Bot?",
            default=has_existing
        ).ask()

        if use_telegram:
            existing_token = self.existing_env.get('TELEGRAM_BOT_TOKEN', '')
            if existing_token:
                print_info("Kosongkan untuk menggunakan token yang sudah ada")
            
            while True:
                bot_token = questionary.password(
                    "Masukkan TELEGRAM BOT TOKEN:",
                    validate=(lambda x: self.validator.validate_token(x)[0]) if not existing_token else None
                ).ask()

                if bot_token:
                    self.config['TELEGRAM_BOT_TOKEN'] = bot_token
                    print_success("Telegram Bot Token disimpan")
                    break
                elif existing_token:
                    self.config['TELEGRAM_BOT_TOKEN'] = existing_token
                    print_info("Menggunakan token yang sudah ada")
                    break

            existing_chat_id = self.existing_env.get('TELEGRAM_CHAT_ID', '')
            default_chat_id = existing_chat_id if existing_chat_id else ''

            while True:
                chat_id = questionary.text(
                    "Masukkan TELEGRAM CHAT ID:",
                    default=default_chat_id,
                    validate=(lambda x: self.validator.validate_chat_id(x)[0]) if not existing_chat_id else None
                ).ask()

                if chat_id:
                    self.config['TELEGRAM_CHAT_ID'] = chat_id
                    print_success("Telegram Chat ID disimpan")
                    return True
                elif existing_chat_id:
                    self.config['TELEGRAM_CHAT_ID'] = existing_chat_id
                    print_info("Menggunakan Chat ID yang sudah ada")
                    return True
                break
        else:
            self.config['TELEGRAM_BOT_TOKEN'] = ""
            self.config['TELEGRAM_CHAT_ID'] = ""
            print_info("Telegram Bot dilewatkan")
            return True

    def _step_database(self) -> bool:
        """Step 4: Choose Database"""
        step = 4
        total = 10
        
        existing_db_url = self.existing_env.get('DATABASE_URL', '')
        existing_db_type = self.existing_env.get('DATABASE_TYPE', 'sqlite')
        
        if existing_db_url:
            print_info(f"Database sudah terisi ({existing_db_url[:40]}...)")
            keep = questionary.confirm("Ubah database?", default=False).ask()
            if not keep:
                self.config['DATABASE_URL'] = existing_db_url
                self.config['DATABASE_TYPE'] = existing_db_type
                print_info("Database tidak diubah")
                return True
        
        databases = ["SQLite", "MySQL"]
        default_idx = 1
        for i, db in enumerate(databases):
            if existing_db_type and existing_db_type.startswith(db.lower()):
                default_idx = i + 1
                break

        print_step(step, total, "Pilih Database:")
        console.print("\nOpsi:")
        for i, db in enumerate(databases, 1):
            marker = " [cyan](current)[/cyan]" if i == default_idx else ""
            console.print(f"  {i}. {db}{marker}")

        while True:
            choice = questionary.text(
                f"\nInput (1-{len(databases)}):",
                default=str(default_idx),
                validate=lambda x: self.validator.validate_choice(x, databases)[0]
            ).ask()

            if choice:
                idx = int(choice) - 1
                db_type = databases[idx]
                self.config['DATABASE_TYPE'] = db_type.lower()
                
                if db_type.lower() == 'sqlite':
                    db_path = questionary.text(
                        "Database path:",
                        default=self.existing_env.get('DATABASE_PATH', 'app/database/stock.db')
                    ).ask()
                    db_url = f"sqlite:///{db_path}"
                else:
                    # MySQL configuration
                    host = questionary.text(
                        "MySQL Host:",
                        default="localhost"
                    ).ask()
                    port = questionary.text(
                        "MySQL Port:",
                        default="3306"
                    ).ask()
                    user = questionary.text(
                        "MySQL User:",
                        default="root"
                    ).ask()
                    password = questionary.password("MySQL Password:").ask()
                    db_name = questionary.text(
                        "Database Name:",
                        default="analisa_saham"
                    ).ask()
                    
                    db_url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}"

                self.config['DATABASE_URL'] = db_url
                print_success(f"Database: {db_type}")
                return True

    def _step_learning_settings(self) -> bool:
        """Step 5: Enable Auto Learning"""
        step = 5
        total = 10
        
        current = self.existing_env.get('AUTO_LEARNING', 'true') == 'true'
        print_step(step, total, "Enable Auto Learning?")

        auto_learning = questionary.confirm(
            "Enable Auto Learning?",
            default=current
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
        current_risk = self.existing_env.get('DEFAULT_RISK_LEVEL', 'moderate').lower()
        default_idx = 1
        for i, m in enumerate(risk_modes):
            if m.lower() == current_risk:
                default_idx = i + 1
                break

        print_step(step, total, "Pilih Risk Mode:")
        console.print("\nOpsi:")
        for i, mode in enumerate(risk_modes, 1):
            marker = " [cyan](current)[/cyan]" if i == default_idx else ""
            console.print(f"  {i}. {mode}{marker}")

        while True:
            choice = questionary.text(
                "\nInput (1-3):",
                default=str(default_idx),
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
        
        current_interval = str(self.existing_env.get('MONITOR_INTERVAL', '15'))
        print_step(step, total, "Interval Monitoring (minutes)")

        while True:
            interval = questionary.text(
                f"Interval (min: 1, max: 1440):",
                default=current_interval,
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
        
        existing_enabled = self.existing_env.get('OLLAMA_ENABLED', 'false') == 'true'
        print_step(step, total, "Enable Local AI Fallback (Ollama)?")

        if existing_enabled:
            print_info(f"Ollama Fallback sudah aktif ({self.existing_env.get('OLLAMA_BASE_URL', '')})")

        enable_ollama = questionary.confirm(
            "Enable Ollama Local Fallback?",
            default=existing_enabled
        ).ask()

        if enable_ollama:
            ollama_url = questionary.text(
                "Ollama URL:",
                default=self.existing_env.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
                validate=lambda x: self.validator.validate_url(x)[0]
            ).ask()

            if ollama_url:
                self.config['OLLAMA_ENABLED'] = "true"
                self.config['OLLAMA_BASE_URL'] = ollama_url
                self.config['OLLAMA_MODEL'] = self.existing_env.get('OLLAMA_MODEL', 'llama3')
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
            "Min Confidence Threshold (range: 0-100):",
            default=str(self.existing_env.get('MIN_CONFIDENCE_THRESHOLD', '50')),
            validate=lambda x: self.validator.validate_integer(x, 0, 100)[0]
        ).ask()

        if threshold:
            self.config['MIN_CONFIDENCE_THRESHOLD'] = int(threshold)
            self.settings['min_confidence_threshold'] = int(threshold)

        # App port
        port = questionary.text(
            "App Port:",
            default=str(self.existing_env.get('APP_PORT', '8000')),
            validate=lambda x: self.validator.validate_integer(x, 1024, 65535)[0]
        ).ask()

        if port:
            self.config['APP_PORT'] = int(port)

        # Debug mode
        current_debug = self.existing_env.get('DEBUG', 'true') == 'true'
        debug = questionary.confirm(
            "Enable Debug Mode?",
            default=current_debug
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

        # Test 9Router
        api_key = self.config.get('NINE_ROUTER_API_KEY')
        if api_key:
            if test_connection('9router', api_key):
                print_success("9Router API connection OK")
            else:
                print_error("9Router API connection failed")

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
