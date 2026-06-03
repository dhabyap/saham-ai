"""
CLI Manager - Main menu system for application management
"""

import sys
import subprocess
import time
from pathlib import Path
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .setup_wizard import SetupWizard
from .config import ConfigManager
from .helpers import (
    EnvManager, FirstRunDetector,
    print_header, print_success, print_error, print_info
)

console = Console()


class CLIManager:
    """Main CLI menu system"""

    def __init__(self):
        self.env_manager = EnvManager()
        self.first_run_detector = FirstRunDetector()

    def run(self):
        """Run main menu"""
        print_header("AI STOCK ANALYZER MANAGER")

        # Check if first run
        if self.first_run_detector.is_first_run():
            console.print(Panel(
                """[bold yellow]Belum ada konfigurasi![/bold yellow]

Jalankan Setup Wizard terlebih dahulu.""",
                title="Info",
                expand=False
            ))

            if questionary.confirm("Jalankan Setup Wizard sekarang?", default=True).ask():
                wizard = SetupWizard()
                success = wizard.run()
                if success:
                    return
                else:
                    return

        # Main menu loop
        while True:
            console.print("\n[cyan]Pilih aksi:[/cyan]\n")

            action = questionary.select(
                "Pilih opsi:",
                choices=[
                    "Start Web Server",
                    "Start Telegram Bot",
                    "Start Scheduler",
                    "Run AI Training",
                    "View Logs",
                    "Manage Configuration",
                    "Setup Wizard",
                    "View Application Info",
                    "Install Dependencies",
                    "Exit"
                ]
            ).ask()

            if action == "Start Web Server":
                self._start_web_server()
            elif action == "Start Telegram Bot":
                self._start_telegram_bot()
            elif action == "Start Scheduler":
                self._start_scheduler()
            elif action == "Run AI Training":
                self._run_training()
            elif action == "View Logs":
                self._view_logs()
            elif action == "Manage Configuration":
                config_manager = ConfigManager()
                config_manager.run()
            elif action == "Setup Wizard":
                wizard = SetupWizard()
                wizard.run()
            elif action == "View Application Info":
                self._view_app_info()
            elif action == "Install Dependencies":
                self._install_dependencies()
            else:
                console.print("\n[cyan]Goodbye![/cyan]\n")
                break

    def _start_web_server(self):
        """Start web server"""
        print_header("START WEB SERVER", 50)

        env_data = self.env_manager.load()
        if not env_data:
            print_error("Belum ada konfigurasi")
            return

        host = env_data.get('APP_HOST', '0.0.0.0')
        port = env_data.get('APP_PORT', '8000')

        console.print(f"""
[cyan]Starting Web Server...[/cyan]

[bold]Server:[/bold] {host}:{port}
[bold]Dashboard:[/bold] http://localhost:{port}
[bold]API Docs:[/bold] http://localhost:{port}/docs

[yellow]Press Ctrl+C to stop[/yellow]
""")

        try:
            subprocess.run(
                [sys.executable, "run.py"],
                cwd=Path(__file__).parent.parent
            )
        except KeyboardInterrupt:
            print_info("Web server stopped")
        except Exception as e:
            print_error(f"Error starting server: {e}")

    def _start_telegram_bot(self):
        """Start Telegram Bot"""
        print_header("START TELEGRAM BOT", 50)

        env_data = self.env_manager.load()
        if not env_data or not env_data.get('TELEGRAM_BOT_TOKEN'):
            print_error("Telegram Bot belum dikonfigurasi")
            return

        console.print("""
[cyan]Starting Telegram Bot...[/cyan]

[yellow]Press Ctrl+C to stop[/yellow]
""")

        try:
            subprocess.run(
                [sys.executable, "-m", "app.telegram.bot"],
                cwd=Path(__file__).parent.parent
            )
        except KeyboardInterrupt:
            print_info("Telegram bot stopped")
        except Exception as e:
            print_error(f"Error starting bot: {e}")

    def _start_scheduler(self):
        """Start Scheduler"""
        print_header("START SCHEDULER", 50)

        env_data = self.env_manager.load()
        if not env_data:
            print_error("Belum ada konfigurasi")
            return

        interval = env_data.get('SCHEDULER_INTERVAL', '15')

        console.print(f"""
[cyan]Starting Scheduler...[/cyan]

[bold]Interval:[/bold] {interval} minutes
[yellow]Press Ctrl+C to stop[/yellow]
""")

        try:
            subprocess.run(
                [sys.executable, "-m", "app.scheduler.scheduler"],
                cwd=Path(__file__).parent.parent
            )
        except KeyboardInterrupt:
            print_info("Scheduler stopped")
        except Exception as e:
            print_error(f"Error starting scheduler: {e}")

    def _run_training(self):
        """Run AI Training"""
        print_header("RUN AI TRAINING", 50)

        env_data = self.env_manager.load()
        if not env_data:
            print_error("Belum ada konfigurasi")
            return

        confirm = questionary.confirm(
            "Run AI training? This may take a while",
            default=False
        ).ask()

        if confirm:
            console.print("\n[cyan]Starting AI training...[/cyan]")
            try:
                subprocess.run(
                    [sys.executable, "-m", "app.ai.training_engine"],
                    cwd=Path(__file__).parent.parent
                )
            except KeyboardInterrupt:
                print_info("Training stopped")
            except Exception as e:
                print_error(f"Error running training: {e}")

    def _view_logs(self):
        """View application logs"""
        print_header("VIEW LOGS", 50)

        log_dir = Path("logs")
        if not log_dir.exists():
            print_info("No logs directory found")
            return

        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            print_info("No log files found")
            return

        log_files_display = [f.name for f in log_files]
        selected = questionary.select(
            "Select log file:",
            choices=log_files_display
        ).ask()

        if selected:
            log_file = log_dir / selected

            # Show last 50 lines
            console.print(f"\n[cyan]Showing last 50 lines of {selected}:[/cyan]\n")

            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        console.print(line.rstrip())
            except Exception as e:
                print_error(f"Error reading log: {e}")

    def _view_app_info(self):
        """View application information"""
        print_header("APPLICATION INFO", 50)

        try:
            from app.config import Config

            info_table = Table(title="Application Information", show_header=True)
            info_table.add_column("Setting", style="cyan")
            info_table.add_column("Value")

            info = {
                "AI Provider": Config.AI_PROVIDER,
                "Database Type": "SQLite" if "sqlite" in Config.DATABASE_URL else "PostgreSQL",
                "Database URL": Config.DATABASE_URL[:50] + "..." if len(Config.DATABASE_URL) > 50 else Config.DATABASE_URL,
                "App Host": Config.APP_HOST,
                "App Port": str(Config.APP_PORT),
                "Scheduler Interval": f"{Config.SCHEDULER_INTERVAL} minutes",
                "Risk Level": Config.DEFAULT_RISK_LEVEL,
                "Debug Mode": str(Config.DEBUG),
            }

            for key, value in info.items():
                info_table.add_row(key, value)

            console.print(info_table)

        except Exception as e:
            print_error(f"Error loading application info: {e}")

    def _install_dependencies(self):
        """Install/update dependencies"""
        print_header("INSTALL DEPENDENCIES", 50)

        console.print("[cyan]Installing Python dependencies...[/cyan]\n")

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=Path(__file__).parent.parent
            )
            print_success("Dependencies installed successfully")
        except Exception as e:
            print_error(f"Error installing dependencies: {e}")


def main():
    """Main entry point"""
    try:
        manager = CLIManager()
        manager.run()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]\n")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
