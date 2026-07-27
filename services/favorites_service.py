"""Сервіс керування обраними літургійними читаннями."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from services.favorites_database import (
    FavoritesDatabase,
    favorites_db,
)
from utils.dates import normalize_date


@dataclass(frozen=True)
class Favorite:
    reading_date: date
    created_at: str


class FavoritesService:
    def __init__(
        self,
        database: FavoritesDatabase | None = None,
    ) -> None:
        self.database = database or favorites_db

    @staticmethod
    def normalize_date(
        value: str | date | datetime | None,
    ) -> date:
        return normalize_date(value)

    def add(
        self,
        user_id: int,
        value: str | date | datetime | None,
    ) -> bool:
        calendar_date = self.normalize_date(value)
        return self.database.add(user_id, calendar_date.isoformat())

    def remove(
        self,
        user_id: int,
        value: str | date | datetime | None,
    ) -> bool:
        calendar_date = self.normalize_date(value)
        return self.database.remove(user_id, calendar_date.isoformat())

    def exists(
        self,
        user_id: int,
        value: str | date | datetime | None,
    ) -> bool:
        calendar_date = self.normalize_date(value)
        return self.database.exists(user_id, calendar_date.isoformat())

    def get_all(self, user_id: int) -> list[Favorite]:
        return [
            Favorite(
                reading_date=date.fromisoformat(row["reading_date"]),
                created_at=row["created_at"],
            )
            for row in self.database.get_all(user_id)
        ]

    def count(self, user_id: int) -> int:
        return self.database.count(user_id)


favorites_service = FavoritesService()
