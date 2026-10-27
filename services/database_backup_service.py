"""SQLite backup for the MGCE readings database."""

import sqlite3
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo

from config import DATABASE_DIR


def backup_readings_database():
    source = DATABASE_DIR / "readings.db"

    if not source.is_file():
        raise FileNotFoundError(f"Readings database not found: {source}")

    backup_dir = DATABASE_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(
        ZoneInfo("Europe/Kyiv")
    ).strftime("%Y%m%d_%H%M%S_%f")

    destination = backup_dir / f"readings_before_sync_{timestamp}.db"
    temporary = destination.with_suffix(".tmp")

    try:
        with closing(sqlite3.connect(source)) as original:
            with closing(sqlite3.connect(temporary)) as backup:
                original.backup(backup)

        with closing(sqlite3.connect(temporary)) as check:
            result = check.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

        if result != "ok":
            raise RuntimeError(
                f"Backup integrity check failed: {result}"
            )

        temporary.replace(destination)

        backups = sorted(
            backup_dir.glob("readings_before_sync_*.db"),
            key=lambda path: path.name,
            reverse=True,
        )

        for old_backup in backups[8:]:
            try:
                old_backup.unlink()
            except OSError:
                pass

        return destination

    finally:
        temporary.unlink(missing_ok=True)
