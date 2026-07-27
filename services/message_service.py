"""Формування повідомлень із читаннями."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from services.bible_service import BibleService
from services.readings_service import ReadingsService
from utils.dates import format_date, normalize_date

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReadingResponse:
    calendar_date: date
    messages: list[str]


class MessageService:
    def __init__(
        self,
        readings_service: ReadingsService,
        bible_service: BibleService,
    ) -> None:
        self.readings_service = readings_service
        self.bible_service = bible_service

    def build_references(
        self,
        value: str | date | None = None,
    ) -> ReadingResponse:
        calendar_date = normalize_date(value)
        text = (
            f"📅 Читання на {format_date(calendar_date)}\n\n"
            f"{self.readings_service.format_readings(calendar_date)}"
        )
        return ReadingResponse(calendar_date, [text])

    def build_full_text(
        self,
        value: str | date | None = None,
    ) -> ReadingResponse:
        calendar_date = normalize_date(value)
        grouped = self.readings_service.get_grouped_references(
            calendar_date
        )

        sections = (
            ("📜 Старий Завіт", grouped["old_testament"]),
            ("📖 Апостол", grouped["apostle"]),
            ("✝️ Євангеліє", grouped["gospel"]),
        )

        result = [
            f"📅 Повний текст читань на {format_date(calendar_date)}"
        ]
        found = False

        for title, references in sections:
            for position, reference in enumerate(references, start=1):
                found = True
                number = f" №{position}" if len(references) > 1 else ""

                try:
                    passage = self.bible_service.get_passage(reference)
                    result.append(
                        f"{title}{number}\n"
                        f"🔖 {reference}\n\n"
                        f"{passage}"
                    )
                except Exception as error:
                    logger.exception(
                        "Не вдалося завантажити %s",
                        reference,
                    )
                    result.append(
                        f"{title}{number}\n"
                        f"🔖 {reference}\n\n"
                        f"Не вдалося отримати повний текст: {error}"
                    )

        if not found:
            result = [
                f"На {format_date(calendar_date)} читання не знайдено."
            ]
        else:
            result.append("🙏 Слава Тобі, Господи!")

        return ReadingResponse(calendar_date, result)
