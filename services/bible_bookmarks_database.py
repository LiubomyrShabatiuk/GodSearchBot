"""SQLite storage for Bible chapter bookmarks."""

import sqlite3
from contextlib import closing
from pathlib import Path

from config import DATABASE_DIR


class BibleBookmarksDatabase:
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
            connection.execute("""
                CREATE TABLE IF NOT EXISTS bible_bookmarks (
                    user_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    chapter INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, book_id, chapter),
                    CHECK (user_id > 0),
                    CHECK (book_id > 0),
                    CHECK (chapter > 0)
                )
            """)

    @staticmethod
    def validate(*values: int) -> None:
        for value in values:
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise ValueError("Invalid bookmark value")

    def add(self, user_id: int, book_id: int, chapter: int) -> bool:
        self.validate(user_id, book_id, chapter)

        with closing(self.connect()) as connection, connection:
            cursor = connection.execute("""
                INSERT OR IGNORE INTO bible_bookmarks
                    (user_id, book_id, chapter)
                VALUES (?, ?, ?)
            """, (user_id, book_id, chapter))
            return cursor.rowcount > 0

    def remove(self, user_id: int, book_id: int, chapter: int) -> bool:
        self.validate(user_id, book_id, chapter)

        with closing(self.connect()) as connection, connection:
            cursor = connection.execute("""
                DELETE FROM bible_bookmarks
                WHERE user_id = ? AND book_id = ? AND chapter = ?
            """, (user_id, book_id, chapter))
            return cursor.rowcount > 0

    def exists(self, user_id: int, book_id: int, chapter: int) -> bool:
        self.validate(user_id, book_id, chapter)

        with closing(self.connect()) as connection:
            row = connection.execute("""
                SELECT 1 FROM bible_bookmarks
                WHERE user_id = ? AND book_id = ? AND chapter = ?
            """, (user_id, book_id, chapter)).fetchone()
            return row is not None

    def get_all(self, user_id: int) -> list[dict]:
        self.validate(user_id)

        with closing(self.connect()) as connection:
            rows = connection.execute("""
                SELECT book_id, chapter, created_at
                FROM bible_bookmarks
                WHERE user_id = ?
                ORDER BY created_at DESC, rowid DESC
            """, (user_id,)).fetchall()
            return [dict(row) for row in rows]
