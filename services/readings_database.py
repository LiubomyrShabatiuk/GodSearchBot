"""
SQLite база літургійних читань.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import DATABASE_DIR
from typing import Iterable


APOSTLE = 1
GOSPEL = 2
OLD_TESTAMENT = 3

VALID_READING_TYPES = {
    APOSTLE,
    GOSPEL,
    OLD_TESTAMENT,
}


class ReadingsDatabase:
    def __init__(
        self,
        db_path: str | Path = DATABASE_DIR / "readings.db",
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
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    reading_type INTEGER NOT NULL,
                    reference TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(date, reading_type, position)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_readings_date
                ON readings(date)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_readings_date_type
                ON readings(date, reading_type)
                """
            )

    @staticmethod
    def validate_reading(
        date: str,
        reading_type: int,
        reference: str,
        position: int,
    ) -> None:
        if not isinstance(date, str) or not date.strip():
            raise ValueError("date має бути непорожнім рядком.")

        if reading_type not in VALID_READING_TYPES:
            raise ValueError(
                f"Невідомий reading_type: {reading_type}"
            )

        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(
                "reference має бути непорожнім рядком."
            )

        if not isinstance(position, int) or position < 1:
            raise ValueError(
                "position має бути цілим числом від 1."
            )

    def save(
        self,
        date: str,
        reading_type: int,
        reference: str,
        position: int = 1,
    ) -> None:
        self.validate_reading(
            date,
            reading_type,
            reference,
            position,
        )

        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO readings (
                    date,
                    reading_type,
                    reference,
                    position
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    date.strip(),
                    reading_type,
                    reference.strip(),
                    position,
                ),
            )

    def save_many(
        self,
        readings: Iterable[tuple[str, int, str, int]],
    ) -> int:
        prepared: list[tuple[str, int, str, int]] = []

        for date, reading_type, reference, position in readings:
            self.validate_reading(
                date,
                reading_type,
                reference,
                position,
            )

            prepared.append(
                (
                    date.strip(),
                    reading_type,
                    reference.strip(),
                    position,
                )
            )

        if not prepared:
            return 0

        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO readings (
                    date,
                    reading_type,
                    reference,
                    position
                )
                VALUES (?, ?, ?, ?)
                """,
                prepared,
            )

        return len(prepared)

    def replace_date(
        self,
        date: str,
        readings: Iterable[tuple[int, str, int]],
    ) -> int:
        prepared: list[tuple[str, int, str, int]] = []

        for reading_type, reference, position in readings:
            self.validate_reading(
                date,
                reading_type,
                reference,
                position,
            )

            prepared.append(
                (
                    date.strip(),
                    reading_type,
                    reference.strip(),
                    position,
                )
            )

        with self.connect() as connection:
            connection.execute(
                "DELETE FROM readings WHERE date = ?",
                (date.strip(),),
            )

            if prepared:
                connection.executemany(
                    """
                    INSERT INTO readings (
                        date,
                        reading_type,
                        reference,
                        position
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    prepared,
                )

        return len(prepared)

    def delete_date(self, date: str) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM readings WHERE date = ?",
                (date.strip(),),
            )
            return cursor.rowcount

    def get(self, date: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    date,
                    reading_type,
                    reference,
                    position
                FROM readings
                WHERE date = ?
                ORDER BY reading_type, position
                """,
                (date.strip(),),
            )
            return cursor.fetchall()

    def get_by_type(
        self,
        date: str,
        reading_type: int,
    ) -> list[sqlite3.Row]:
        if reading_type not in VALID_READING_TYPES:
            raise ValueError(
                f"Невідомий reading_type: {reading_type}"
            )

        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    date,
                    reading_type,
                    reference,
                    position
                FROM readings
                WHERE date = ?
                  AND reading_type = ?
                ORDER BY position
                """,
                (date.strip(), reading_type),
            )
            return cursor.fetchall()

    def get_all(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    date,
                    reading_type,
                    reference,
                    position
                FROM readings
                ORDER BY date, reading_type, position
                """
            )
            return cursor.fetchall()

    def count(self, date: str | None = None) -> int:
        with self.connect() as connection:
            if date is None:
                cursor = connection.execute(
                    "SELECT COUNT(*) FROM readings"
                )
            else:
                cursor = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM readings
                    WHERE date = ?
                    """,
                    (date.strip(),),
                )

            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM readings"
            )


readings_db = ReadingsDatabase()


if __name__ == "__main__":
    db = ReadingsDatabase()

    print("База даних готова.")
    print(f"Записів: {db.count()}")
