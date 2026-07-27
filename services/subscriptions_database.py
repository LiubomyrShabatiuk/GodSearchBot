"""SQLite-база підписок на щоденні читання."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from config import DATABASE_DIR


class SubscriptionsDatabase:
    def __init__(
        self,
        db_path: str | Path = DATABASE_DIR / "readings.db",
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_table()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_table(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    chat_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    username TEXT,
                    full_name TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add(
        self,
        chat_id: int,
        user_id: int | None = None,
        username: str | None = None,
        full_name: str | None = None,
    ) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO subscriptions (
                    chat_id,
                    user_id,
                    username,
                    full_name
                )
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, user_id, username, full_name),
            )
            return cursor.rowcount > 0

    def remove(self, chat_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM subscriptions WHERE chat_id = ?",
                (chat_id,),
            )
            return cursor.rowcount > 0

    def exists(self, chat_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT 1
                FROM subscriptions
                WHERE chat_id = ?
                LIMIT 1
                """,
                (chat_id,),
            )
            return cursor.fetchone() is not None

    def get_all_chat_ids(self) -> list[int]:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT chat_id
                FROM subscriptions
                ORDER BY created_at
                """
            )
            return [int(row["chat_id"]) for row in cursor.fetchall()]

    def count(self) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "SELECT COUNT(*) FROM subscriptions"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0


subscriptions_db = SubscriptionsDatabase()
