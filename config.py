"""Єдина конфігурація GodSearchBot."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
LOG_DIR = BASE_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"

for folder in (DATA_DIR, DATABASE_DIR, LOG_DIR, CACHE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не знайдено у файлі .env")

USERS_DB = DATABASE_DIR / "users.db"
BIBLE_DB = DATABASE_DIR / "bible.db"

DEFAULT_LANGUAGE = "uk"
SUPPORTED_LANGUAGES = ("uk", "en")

LOG_LEVEL = "INFO"
LOG_FILE = LOG_DIR / "bot.log"

MAX_MESSAGE_LENGTH = 4000
TELEGRAM_SAFE_MESSAGE_LENGTH = 3900

VERSION = "2.1.0"
