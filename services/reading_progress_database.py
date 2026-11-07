"""SQLite storage for the last opened Bible chapter."""

import sqlite3
from contextlib import closing
from pathlib import Path

from config import DATABASE_DIR


class ReadingProgressDatabase:
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
        with closing(self.connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reading_progress (
                    user_id INTEGER PRIMARY KEY,
                    book_id INTEGER NOT NULL,
                    chapter INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    CHECK (book_id > 0),
                    CHECK (chapter > 0)
                )
                """
            )

    def save(
        self,
        user_id: int,
        book_id: int,
        chapter: int,
    ) -> None:
        for value in (user_id, book_id, chapter):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise ValueError("Invalid reading progress value")

        with closing(self.connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO reading_progress (
                    user_id, book_id, chapter
                )
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    book_id = excluded.book_id,
                    chapter = excluded.chapter,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, book_id, chapter),
            )

    def get(self, user_id: int) -> dict | None:
        if (
            not isinstance(user_id, int)
            or isinstance(user_id, bool)
            or user_id <= 0
        ):
            raise ValueError("Invalid user ID")

        with closing(self.connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT book_id, chapter, updated_at
                FROM reading_progress
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        return dict(row) if row else None


