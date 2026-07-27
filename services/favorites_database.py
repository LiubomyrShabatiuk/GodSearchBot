"""SQLite-сховище обраних літургійних читань."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parents[1] / "database" / "readings.db"
)


class FavoritesDatabase:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DATABASE_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_tables(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reading_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, reading_date)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_favorites_user_created
                ON favorites(user_id, created_at DESC)
                """
            )

    @staticmethod
    def _validate_user_id(user_id: int) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id має бути додатним цілим числом.")

    @staticmethod
    def _validate_reading_date(reading_date: str) -> None:
        if not isinstance(reading_date, str) or not reading_date.strip():
            raise ValueError("reading_date має бути непорожнім рядком.")

        try:
            datetime.strptime(reading_date.strip(), "%Y-%m-%d")
        except ValueError as error:
            raise ValueError(
                "reading_date має бути у форматі YYYY-MM-DD."
            ) from error

    def add(self, user_id: int, reading_date: str) -> bool:
        self._validate_user_id(user_id)
        self._validate_reading_date(reading_date)

        created_at = datetime.now(timezone.utc).isoformat()

        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO favorites (
                    user_id,
                    reading_date,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (user_id, reading_date.strip(), created_at),
            )
            return cursor.rowcount > 0

    def remove(self, user_id: int, reading_date: str) -> bool:
        self._validate_user_id(user_id)
        self._validate_reading_date(reading_date)

        with self.connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM favorites
                WHERE user_id = ? AND reading_date = ?
                """,
                (user_id, reading_date.strip()),
            )
            return cursor.rowcount > 0

    def exists(self, user_id: int, reading_date: str) -> bool:
        self._validate_user_id(user_id)
        self._validate_reading_date(reading_date)

        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT 1
                FROM favorites
                WHERE user_id = ? AND reading_date = ?
                LIMIT 1
                """,
                (user_id, reading_date.strip()),
            )
            return cursor.fetchone() is not None

    def get_all(self, user_id: int) -> list[sqlite3.Row]:
        self._validate_user_id(user_id)

        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, user_id, reading_date, created_at
                FROM favorites
                WHERE user_id = ?
                ORDER BY reading_date DESC, created_at DESC
                """,
                (user_id,),
            )
            return cursor.fetchall()

    def count(self, user_id: int) -> int:
        self._validate_user_id(user_id)

        with self.connect() as connection:
            cursor = connection.execute(
                "SELECT COUNT(*) FROM favorites WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0


favorites_db = FavoritesDatabase()
