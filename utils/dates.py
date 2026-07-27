"""Робота з календарними датами."""
from __future__ import annotations

from datetime import date, datetime

SUPPORTED_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y")


def normalize_date(value: str | date | datetime | None = None) -> date:
    """Повертає дату як datetime.date."""
    if value is None:
        return date.today()

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise TypeError("Дата має бути рядком, date, datetime або None.")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Дата не може бути порожньою.")

    for date_format in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue

    raise ValueError(
        "Неправильний формат дати. "
        "Використовуйте YYYY-MM-DD або DD.MM.YYYY."
    )


def format_date(value: str | date | datetime | None = None) -> str:
    """Форматує дату для показу користувачу."""
    return normalize_date(value).strftime("%d.%m.%Y")
