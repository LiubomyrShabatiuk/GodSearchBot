"""Reliable weekly synchronization of the MGCE calendar."""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

from config import DATABASE_DIR
from importers.mgce_importer import MgceImporter
from services.database_backup_service import backup_readings_database

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("Europe/Kyiv")
SYNC_WEEKDAY = 0
SYNC_HOUR = 3
SYNC_MINUTE = 0
CHECK_INTERVAL = 60

STATE_FILE = DATABASE_DIR / "calendar_sync_state.json"
_sync_lock = Lock()


def scheduled_sync_date(now):
    days_since_monday = now.weekday()
    scheduled = (now - timedelta(days=days_since_monday)).replace(
        hour=SYNC_HOUR,
        minute=SYNC_MINUTE,
        second=0,
        microsecond=0,
    )
    if scheduled > now:
        scheduled -= timedelta(days=7)
    return scheduled.date()


def last_successful_sync():
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("last_successful_week")
    except (OSError, ValueError, TypeError):
        logger.exception("Could not read calendar sync state")
        return None


def save_successful_sync(week):
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"last_successful_week": week}),
        encoding="utf-8",
    )
    os.replace(temporary, STATE_FILE)


def sync_calendar_if_due():
    if not _sync_lock.acquire(blocking=False):
        logger.info("Calendar sync already running; skipping")
        return

    try:
        now = datetime.now(TIMEZONE)
        scheduled = scheduled_sync_date(now)
        week = scheduled.isoformat()

        if last_successful_sync() == week:
            return

        year = now.year
        logger.info("Starting MGCE calendar sync: year=%s, week=%s", year, week)

        backup_path = backup_readings_database()
        logger.info("Calendar database backup created: %s", backup_path)

        importer = MgceImporter(year=year)
        result = importer.import_year()

        if result["errors"] or result["days_without_readings"]:
            raise RuntimeError("Calendar sync reported validation errors")

        save_successful_sync(week)

        logger.info(
            "MGCE calendar sync successful: days=%s, readings=%s",
            result["days_processed"],
            result["readings_saved"],
        )
    finally:
        _sync_lock.release()


async def weekly_calendar_sync_loop():
    logger.info("MGCE calendar sync scheduler started")

    while True:
        try:
            await asyncio.to_thread(sync_calendar_if_due)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("MGCE calendar synchronization failed")

        await asyncio.sleep(CHECK_INTERVAL)
