"""
Helper functions for CLI operations
"""

import os
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import dotenv_values, set_key
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

console = Console()


class EnvManager:
    """Manage .env file operations"""

    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        self.env_file = Path(env_path)

    def load(self) -> Dict[str, str]:
        """Load existing .env file"""
        if self.env_file.exists():
            return dotenv_values(self.env_path)
        return {}

    def save(self, data: Dict[str, str]) -> bool:
        """Save data to .env file"""
        try:
            for key, value in data.items():
                set_key(self.env_path, key, str(value))
            return True
        except Exception as e:
            console.print(f"[red]Error saving .env: {e}[/red]")
            return False

    def exists(self) -> bool:
        """Check if .env file exists"""
        return self.env_file.exists()


class SettingsManager:
    """Manage settings.json file operations"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.settings_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load existing settings.json"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Error loading settings: {e}[/yellow]")
                return self.get_default_settings()
        return self.get_default_settings()

    def save(self, data: Dict[str, Any]) -> bool:
        """Save settings to settings.json"""
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            console.print(f"[red]Error saving settings: {e}[/red]")
            return False

    @staticmethod
    def get_default_settings() -> Dict[str, Any]:
        """Get default settings template"""
        return {
            "app_name": "AI Stock Analyzer",
            "app_version": "1.0.0",
            "auto_learning": True,
            "risk_mode": "moderate",
            "monitor_interval": 15,
            "ollama_enabled": False,
            "min_confidence_threshold": 50,
            "default_strategy": "swing",
            "max_portfolio_stocks": 10,
            "log_level": "INFO",
            "language": "id",
            "theme": "dark"
        }


class FirstRunDetector:
    """Detect if this is first run of application"""

    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path

    def is_first_run(self) -> bool:
        """Check if .env file doesn't exist"""
        return not Path(self.env_path).exists()

    def mark_initialized(self) -> bool:
        """Create marker that setup is done"""
        return Path(self.env_path).exists()


def print_header(title: str, width: int = 50):
    """Print formatted header"""
    console.print(f"\n{Fore.CYAN}{'=' * width}{Style.RESET_ALL}")
    console.print(f"{Fore.CYAN} {title.center(width - 2)}{Style.RESET_ALL}")
    console.print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}\n")


def print_step(step: int, total: int, question: str):
    """Print step indicator"""
    console.print(f"[cyan][[{step}/{total}]][/cyan] {question}")


def print_success(message: str):
    """Print success message"""
    console.print(f"[green]✓ {message}[/green]")


def print_error(message: str):
    """Print error message"""
    console.print(f"[red]✗ {message}[/red]")


def print_warning(message: str):
    """Print warning message"""
    console.print(f"[yellow]⚠ {message}[/yellow]")


def print_info(message: str):
    """Print info message"""
    console.print(f"[blue]ℹ {message}[/blue]")


def print_table(title: str, data: Dict[str, str]):
    """Print formatted table"""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="dim")
    table.add_column("Value")

    for key, value in data.items():
        # Hide sensitive values
        if 'key' in key.lower() or 'token' in key.lower():
            value = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
        table.add_row(key, str(value))

    console.print(table)


def create_directories(dirs: list):
    """Create required directories"""
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def test_connection(provider: str, api_key: str, test_func=None) -> bool:
    """Test API connection"""
    try:
        if provider.lower() == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            client.models.list()
            return True
        
        elif provider.lower() == "gemini":
            from google import genai
            client = genai.Client(api_key=api_key)
            client.models.list()
            return True
        
        elif provider.lower() == "ollama":
            import requests
            response = requests.get(f"{api_key}/api/tags", timeout=5)
            return response.status_code == 200

        elif provider.lower() == "openrouter":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            client.models.list()
            return True

        elif provider.lower() == "groq":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            client.models.list()
            return True

        return True
    except Exception as e:
        console.print(f"[red]Connection test failed: {e}[/red]")
        return False
