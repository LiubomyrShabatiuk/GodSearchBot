"""Сервіс отримання літургійних читань із SQLite."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from services.readings_database import (
    APOSTLE,
    GOSPEL,
    OLD_TESTAMENT,
    ReadingsDatabase,
    readings_db,
)
from utils.dates import normalize_date

READING_TYPE_NAMES = {
    APOSTLE: "Апостол",
    GOSPEL: "Євангеліє",
    OLD_TESTAMENT: "Старий Завіт",
}


class ReadingsService:
    def __init__(self, database: ReadingsDatabase | None = None) -> None:
        self.database = database or readings_db

    @staticmethod
    def normalize_date(
        value: str | date | datetime | None = None,
    ) -> str:
        return normalize_date(value).isoformat()

    @staticmethod
    def reading_type_name(reading_type: int) -> str:
        return READING_TYPE_NAMES.get(
            reading_type,
            f"Невідомий тип {reading_type}",
        )

    @staticmethod
    def row_to_dict(row: Any) -> dict[str, Any]:
        reading_type = row["reading_type"]
        return {
            "id": row["id"],
            "date": row["date"],
            "reading_type": reading_type,
            "reading_type_name": READING_TYPE_NAMES.get(
                reading_type,
                f"Невідомий тип {reading_type}",
            ),
            "reference": row["reference"],
            "position": row["position"],
        }

    def get_readings(
        self,
        value: str | date | datetime | None = None,
    ) -> list[dict[str, Any]]:
        calendar_date = self.normalize_date(value)
        return [
            self.row_to_dict(row)
            for row in self.database.get(calendar_date)
        ]

    def get_readings_by_type(
        self,
        value: str | date | datetime | None,
        reading_type: int,
    ) -> list[dict[str, Any]]:
        calendar_date = self.normalize_date(value)
        rows = self.database.get_by_type(calendar_date, reading_type)
        return [self.row_to_dict(row) for row in rows]

    def get_references_by_type(
        self,
        value: str | date | datetime | None,
        reading_type: int,
    ) -> list[str]:
        return [
            item["reference"]
            for item in self.get_readings_by_type(value, reading_type)
        ]

    def get_grouped_references(
        self,
        value: str | date | datetime | None = None,
    ) -> dict[str, Any]:
        calendar_date = self.normalize_date(value)
        return {
            "date": calendar_date,
            "old_testament": self.get_references_by_type(
                calendar_date,
                OLD_TESTAMENT,
            ),
            "apostle": self.get_references_by_type(
                calendar_date,
                APOSTLE,
            ),
            "gospel": self.get_references_by_type(
                calendar_date,
                GOSPEL,
            ),
        }

    def has_readings(
        self,
        value: str | date | datetime | None = None,
    ) -> bool:
        return self.database.count(self.normalize_date(value)) > 0

    def format_readings(
        self,
        value: str | date | datetime | None = None,
    ) -> str:
        grouped = self.get_grouped_references(value)
        sections: list[str] = []

        section_data = (
            ("📜 Старий Завіт", grouped["old_testament"]),
            ("📖 Апостол", grouped["apostle"]),
            ("✝️ Євангеліє", grouped["gospel"]),
        )

        for title, references in section_data:
            if references:
                sections.append(self._format_section(title, references))

        if not sections:
            return f"На {grouped['date']} читання не знайдено."

        return "\n\n".join(sections)

    @staticmethod
    def _format_section(title: str, references: list[str]) -> str:
        if len(references) == 1:
            return f"{title}:\n{references[0]}"

        lines = [
            f"{position}. {reference}"
            for position, reference in enumerate(references, start=1)
        ]
        return f"{title}:\n" + "\n".join(lines)


readings_service = ReadingsService()
