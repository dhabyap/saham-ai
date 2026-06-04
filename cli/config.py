"""
Configuration Editor - Allow users to modify existing configuration
"""

import sys
from pathlib import Path
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .validators import Validator
from .helpers import (
    EnvManager, SettingsManager,
    print_header, print_success, print_error, print_info,
    print_table, test_connection
)

console = Console()
validator = Validator()


class ConfigManager:
    """Manage and edit existing configuration"""

    def __init__(self):
        self.env_manager = EnvManager()
        self.settings_manager = SettingsManager()
        self.validator = Validator()

    def run(self) -> bool:
        """Run configuration editor"""
        print_header("AI STOCK ANALYZER - CONFIG EDITOR")

        while True:
            console.print("\n[cyan]Pilih aksi:[/cyan]\n")
            
            action = questionary.select(
                "Pilih opsi:",
                choices=[
                    "View Current Config",
                    "Edit AI Provider",
                    "Edit API Keys",
                    "Edit Telegram Settings",
                    "Edit Database",
                    "Edit Risk Mode",
                    "Edit Monitoring Settings",
                    "Test Connections",
                    "Reset Configuration",
                    "Back to Main Menu"
                ]
            ).ask()

            if action == "View Current Config":
                self._view_config()
            elif action == "Edit AI Provider":
                self._edit_ai_provider()
            elif action == "Edit API Keys":
                self._edit_api_keys()
            elif action == "Edit Telegram Settings":
                self._edit_telegram()
            elif action == "Edit Database":
                self._edit_database()
            elif action == "Edit Risk Mode":
                self._edit_risk_mode()
            elif action == "Edit Monitoring Settings":
                self._edit_monitoring()
            elif action == "Test Connections":
                self._test_connections()
            elif action == "Reset Configuration":
                self._reset_config()
            else:
                return True

    def _view_config(self):
        """View current configuration"""
        print_header("CURRENT CONFIGURATION", 50)

        env_data = self.env_manager.load()
        settings_data = self.settings_manager.load()

        if not env_data:
            print_info("Belum ada konfigurasi. Jalankan setup wizard terlebih dahulu.")
            return

        # Show .env config
        config_display = {}
        for key, value in env_data.items():
            if 'key' in key.lower() or 'token' in key.lower():
                config_display[key] = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
            else:
                config_display[key] = value

        print_table(".env Configuration", config_display)

        # Show settings.json
        if settings_data:
            print_table("settings.json Configuration", {
                k: str(v) for k, v in settings_data.items()
            })

    def _edit_ai_provider(self):
        """Edit AI Provider"""
        env_data = self.env_manager.load()
        current = env_data.get('AI_PROVIDER', 'openai')

        providers = ["openai", "gemini", "ollama", "openrouter", "groq", "9router"]

        new_provider = questionary.select(
            f"Current: {current}",
            choices=providers
        ).ask()

        if new_provider:
            env_data['AI_PROVIDER'] = new_provider
            self.env_manager.save(env_data)
            print_success(f"AI Provider changed to: {new_provider}")

    def _edit_api_keys(self):
        """Edit API Keys"""
        env_data = self.env_manager.load()
        provider = env_data.get('AI_PROVIDER', 'openai')

        console.print(f"\n[cyan]Edit {provider.upper()} API Key[/cyan]")

        if provider.lower() == 'openai':
            key = questionary.password("OpenAI API Key:").ask()
            if key:
                env_data['OPENAI_API_KEY'] = key
                model = questionary.text(
                    "OpenAI Model (default: gpt-4-turbo):",
                    default=env_data.get('OPENAI_MODEL', 'gpt-4-turbo')
                ).ask()
                if model:
                    env_data['OPENAI_MODEL'] = model
                print_success("OpenAI API Key updated")

        elif provider.lower() == 'gemini':
            key = questionary.password("Gemini API Key:").ask()
            if key:
                env_data['GEMINI_API_KEY'] = key
                model = questionary.text(
                    "Gemini Model (default: gemini-2.0-flash):",
                    default=env_data.get('GEMINI_MODEL', 'gemini-2.0-flash')
                ).ask()
                if model:
                    env_data['GEMINI_MODEL'] = model
                print_success("Gemini API Key updated")

        elif provider.lower() == 'ollama':
            url = questionary.text(
                "Ollama URL:",
                default=env_data.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            ).ask()
            if url:
                env_data['OLLAMA_BASE_URL'] = url
                model = questionary.text(
                    "Ollama Model (default: llama3):",
                    default=env_data.get('OLLAMA_MODEL', 'llama3')
                ).ask()
                if model:
                    env_data['OLLAMA_MODEL'] = model
                print_success("Ollama settings updated")

        elif provider.lower() == '9router':
            url = questionary.text(
                "9Router Base URL:",
                default=env_data.get('NINE_ROUTER_BASE_URL', 'http://localhost:20128/v1')
            ).ask()
            if url:
                env_data['NINE_ROUTER_BASE_URL'] = url
                model = questionary.text(
                    "9Router Model (default: openai/gpt-4o-mini):",
                    default=env_data.get('NINE_ROUTER_MODEL', 'openai/gpt-4o-mini')
                ).ask()
                if model:
                    env_data['NINE_ROUTER_MODEL'] = model
                if not env_data.get('NINE_ROUTER_API_KEY'):
                    env_data['NINE_ROUTER_API_KEY'] = 'sk-9router'
                print_success("9Router settings updated")

        if env_data:
            self.env_manager.save(env_data)

    def _edit_telegram(self):
        """Edit Telegram Settings"""
        env_data = self.env_manager.load()

        console.print("\n[cyan]Edit Telegram Settings[/cyan]")

        token = questionary.password(
            f"Telegram Bot Token (current: {'***' if env_data.get('TELEGRAM_BOT_TOKEN') else 'not set'}):",
            default=""
        ).ask()

        if token:
            env_data['TELEGRAM_BOT_TOKEN'] = token

        chat_id = questionary.text(
            f"Telegram Chat ID (current: {env_data.get('TELEGRAM_CHAT_ID', 'not set')}):",
            default=env_data.get('TELEGRAM_CHAT_ID', '')
        ).ask()

        if chat_id:
            valid, msg = validator.validate_chat_id(chat_id)
            if valid:
                env_data['TELEGRAM_CHAT_ID'] = chat_id
                print_success("Telegram settings updated")
            else:
                print_error(f"Invalid Chat ID: {msg}")
                return

        if env_data:
            self.env_manager.save(env_data)

    def _edit_database(self):
        """Edit Database Settings"""
        env_data = self.env_manager.load()

        console.print("\n[cyan]Edit Database Settings[/cyan]")

        db_type = questionary.select(
            f"Database Type:",
            choices=["sqlite", "postgresql"]
        ).ask()

        if db_type == "sqlite":
            db_path = questionary.text(
                "Database path:",
                default=env_data.get('DATABASE_PATH', 'app/database/stock.db')
            ).ask()
            if db_path:
                env_data['DATABASE_PATH'] = db_path
                env_data['DATABASE_URL'] = f"sqlite:///{db_path}"
                env_data['DATABASE_TYPE'] = 'sqlite'
                print_success("Database settings updated")

        elif db_type == "postgresql":
            host = questionary.text(
                "PostgreSQL Host:",
                default="localhost"
            ).ask()
            port = questionary.text(
                "PostgreSQL Port:",
                default="5432"
            ).ask()
            user = questionary.text("PostgreSQL User:").ask()
            password = questionary.password("PostgreSQL Password:").ask()
            db_name = questionary.text("Database Name:").ask()

            if all([host, port, user, password, db_name]):
                db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
                env_data['DATABASE_URL'] = db_url
                env_data['DATABASE_TYPE'] = 'postgresql'
                print_success("Database settings updated")

        if env_data:
            self.env_manager.save(env_data)

    def _edit_risk_mode(self):
        """Edit Risk Mode"""
        env_data = self.env_manager.load()
        settings_data = self.settings_manager.load()

        current = env_data.get('DEFAULT_RISK_LEVEL', 'moderate')

        risk_modes = ["conservative", "moderate", "aggressive"]

        new_mode = questionary.select(
            f"Risk Mode (current: {current}):",
            choices=risk_modes
        ).ask()

        if new_mode:
            env_data['DEFAULT_RISK_LEVEL'] = new_mode
            env_data['RISK_MODE'] = new_mode
            settings_data['risk_mode'] = new_mode
            
            self.env_manager.save(env_data)
            self.settings_manager.save(settings_data)
            print_success(f"Risk Mode changed to: {new_mode}")

    def _edit_monitoring(self):
        """Edit Monitoring Settings"""
        env_data = self.env_manager.load()
        settings_data = self.settings_manager.load()

        current_interval = env_data.get('SCHEDULER_INTERVAL', '15')

        interval = questionary.text(
            f"Monitoring Interval in minutes (current: {current_interval}):",
            validate=lambda x: validator.validate_integer(x, 1, 1440)[0]
        ).ask()

        if interval:
            env_data['SCHEDULER_INTERVAL'] = int(interval)
            env_data['MONITOR_INTERVAL'] = int(interval)
            settings_data['monitor_interval'] = int(interval)
            
            self.env_manager.save(env_data)
            self.settings_manager.save(settings_data)
            print_success(f"Monitoring interval changed to: {interval} minutes")

    def _test_connections(self):
        """Test all connections"""
        print_header("TEST CONNECTIONS", 50)

        env_data = self.env_manager.load()

        if not env_data:
            print_error("Belum ada konfigurasi")
            return

        # Test AI Provider
        provider = env_data.get('AI_PROVIDER', 'openai')
        console.print(f"\n[cyan]Testing {provider.upper()} API...[/cyan]")

        api_key = None
        if provider == 'openai':
            api_key = env_data.get('OPENAI_API_KEY')
        elif provider == 'gemini':
            api_key = env_data.get('GEMINI_API_KEY')
        elif provider == 'ollama':
            api_key = env_data.get('OLLAMA_BASE_URL')
        elif provider == 'openrouter':
            api_key = env_data.get('OPENROUTER_API_KEY')
        elif provider == 'groq':
            api_key = env_data.get('GROQ_API_KEY')
        elif provider == '9router':
            api_key = env_data.get('NINE_ROUTER_API_KEY', 'sk-9router')

        if api_key:
            if test_connection(provider, api_key):
                print_success(f"{provider.upper()} API connection OK")
            else:
                print_error(f"{provider.upper()} API connection failed")
        else:
            print_error(f"No {provider.upper()} API key configured")

        # Test Telegram Bot
        if env_data.get('TELEGRAM_BOT_TOKEN'):
            console.print("\n[cyan]Testing Telegram Bot...[/cyan]")
            try:
                from telegram import Bot
                bot = Bot(token=env_data['TELEGRAM_BOT_TOKEN'])
                bot.get_me()
                print_success("Telegram Bot connection OK")
            except Exception as e:
                print_error(f"Telegram Bot connection failed: {str(e)[:100]}")

        # Test Database
        console.print("\n[cyan]Testing Database...[/cyan]")
        db_url = env_data.get('DATABASE_URL', '')
        if 'sqlite' in db_url:
            db_path = db_url.replace('sqlite:///', '')
            if Path(db_path).parent.exists():
                print_success("SQLite database path OK")
            else:
                print_error("SQLite database path not found")
        else:
            print_info("Database connection test skipped")

    def _reset_config(self):
        """Reset configuration"""
        confirm = questionary.confirm(
            "Reset all configuration? This will delete .env and settings.json",
            default=False
        ).ask()

        if confirm:
            confirm2 = questionary.confirm(
                "Are you sure? This cannot be undone!",
                default=False
            ).ask()

            if confirm2:
                try:
                    env_file = Path(".env")
                    settings_file = Path("config/settings.json")

                    if env_file.exists():
                        env_file.unlink()
                    if settings_file.exists():
                        settings_file.unlink()

                    print_success("Configuration reset. Please run setup wizard again.")
                    console.print("\n[cyan]Run: python cli/setup_wizard.py[/cyan]")
                except Exception as e:
                    print_error(f"Error resetting config: {e}")


def main():
    """Main entry point"""
    manager = ConfigManager()
    manager.run()


if __name__ == "__main__":
    main()
