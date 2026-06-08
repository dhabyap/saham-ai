"""Launch Telegram bot for AI Stock Analyzer."""
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
print("Starting Telegram Bot...", flush=True)

from app.telegram.bot import TelegramBot

print("Bot class imported", flush=True)
bot = TelegramBot()
print("Bot instance created", flush=True)
bot.run()
