"""Tests for Telegram bot commands.

Verifies all command handlers exist, have error handling,
and are properly registered.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.telegram.bot import TelegramBot
from app.services.stock_service import STOCK_LIST


COMMAND_HANDLERS = {
    "start": "start",
    "help": "help_command",
    "analyze": "analyze",
    "add": "add_watchlist",
    "remove": "remove_watchlist",
    "watchlist": "watchlist",
    "topgainer": "top_gainer",
    "toploser": "top_loser",
    "topvolume": "top_volume",
    "market": "market",
    "sentiment": "sentiment",
    "feedback": "feedback_cmd",
    "accuracy": "accuracy_cmd",
    "performance": "performance_cmd",
    "strategy": "strategy_cmd",
    "rekomendasi": "rekomendasi_cmd",
    "daytrade": "daytrade_cmd",
    "bpjs": "daytrade_candidates_cmd",
    "daytradecandidates": "daytrade_candidates_cmd",
    "longterm": "longterm_cmd",
    "longtermcandidates": "longtermcandidates_cmd",
}


SET_COMMANDS = [
    "start", "help", "analyze", "add", "remove", "watchlist",
    "topgainer", "toploser", "topvolume", "market", "sentiment",
    "feedback", "accuracy", "performance", "strategy",
    "rekomendasi", "daytrade", "bpjs", "daytradecandidates",
    "longterm", "longtermcandidates",
]


def test_bot_initializes():
    """Test TelegramBot can be instantiated."""
    bot = TelegramBot()
    assert bot is not None
    assert bot.analysis_service is not None
    assert bot.learning is not None


def test_all_command_handlers_exist():
    """Test every registered command has a corresponding handler method."""
    bot = TelegramBot()
    for cmd, method_name in COMMAND_HANDLERS.items():
        assert hasattr(bot, method_name), f"Missing handler for /{cmd}: {method_name}"
        handler = getattr(bot, method_name)
        assert callable(handler), f"Handler for /{cmd} is not callable"
        assert hasattr(handler, "__code__"), f"Handler for /{cmd} has no code"


def test_set_commands_contains_all():
    """Test set_commands() includes all registered commands."""
    for cmd in SET_COMMANDS:
        assert cmd in BotCommandRegistry(), f"Missing /{cmd} in set_commands()"


def BotCommandRegistry():
    """Extract command names from set_commands() method."""
    bot = TelegramBot()
    import inspect
    source = inspect.getsource(bot.set_commands)
    lines = source.split("\n")
    commands = set()
    for line in lines:
        line = line.strip()
        if 'BotCommand("' in line:
            parts = line.split('"')
            if len(parts) > 1:
                commands.add(parts[1])
    return commands


def test_registered_commands_in_run():
    """Test all commands are registered via add_handler in run()."""
    bot = TelegramBot()
    import inspect
    source = inspect.getsource(bot.run)
    for cmd in COMMAND_HANDLERS:
        assert f'CommandHandler("{cmd}"' in source or f"CommandHandler('{cmd}'" in source, \
            f"/{cmd} not registered in run()"


def test_help_includes_all_commands():
    """Test /help text includes all key commands."""
    bot = TelegramBot()
    import inspect
    help_source = inspect.getsource(bot.help_command)
    key_commands = [
        "/analyze", "/add", "/remove", "/watchlist",
        "/topgainer", "/toploser", "/topvolume",
        "/market", "/sentiment", "/rekomendasi",
        "/daytrade", "/bpjs", "/longterm", "/longtermcandidates",
        "/feedback", "/accuracy", "/performance", "/strategy",
    ]
    for cmd in key_commands:
        assert cmd in help_source, f"/help missing {cmd}"


def test_error_handling_in_all_handlers():
    """Test all handlers have try/except error handling."""
    bot = TelegramBot()
    import inspect
    handlers_to_check = list(COMMAND_HANDLERS.values())
    # Deduplicate (bpjs and daytradecandidates share same handler)
    handlers_to_check = list(set(handlers_to_check))
    for method_name in handlers_to_check:
        handler = getattr(bot, method_name)
        source = inspect.getsource(handler)
        assert "try:" in source, f"{method_name} missing try block"
        assert "except Exception as e:" in source, f"{method_name} missing except Exception"
        assert "print(f\"Error in " in source or 'print("Error in ' in source, \
            f"{method_name} missing error print statement"


def test_help_mentions_all_group1_core():
    """Test /help text mentions all core commands (Group 1)."""
    bot = TelegramBot()
    import inspect
    help_source = inspect.getsource(bot.help_command)
    group1 = ["/analyze", "/rekomendasi", "/add", "/remove", "/watchlist",
              "/topgainer", "/toploser", "/topvolume", "/market", "/sentiment"]
    for cmd in group1:
        assert cmd in help_source, f"/help missing core command {cmd}"
