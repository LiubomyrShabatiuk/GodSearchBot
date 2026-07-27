from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.readings_database import (
    APOSTLE,
    GOSPEL,
    ReadingsDatabase,
)


OLD_TESTAMENT = 3


class MgceImporter:
    """
    Імпортер літургійних читань із локального HTML-календаря МГКЄ.

    Типи читань:
        1 — Апостол
        2 — Євангеліє
        3 — Старий Завіт
    """

    BOOK_PATTERN = (
        r"(?:"

        # Євангелія
        r"Мт|Мф|Мк|Мр|Лк|Лук|Ів|Ин|Йо|"

        # Новий Завіт
        r"Діян|Дії|"
        r"Рм|Рим|"
        r"[1-2]\s*Кр|"
        r"[1-2]\s*Кор|"
        r"Кр|Кор|"
        r"Гал|Еф|Фл|Флп|Кл|Кол|"
        r"[1-2]\s*Сол|Сол|"
        r"[1-2]\s*Тм|"
        r"[1-2]\s*Тим|"
        r"Тм|Тим|Тит|Флм|Євр|"
        r"Як|"
        r"[1-2]\s*Пт|Пт|"
        r"[1-3]\s*Ів|"
        r"Юд|Одкр|"

        # Старий Завіт
        r"Бут|Вих|Лев|Чис|Втор|"
        r"Нав|Суд|Рут|"
        r"[1-4]\s*Цар|"
        r"[1-2]\s*Хр|"
        r"Езд|Неєм|Тов|Юдт|Ест|"
        r"Йов|Пс|Псал|"
        r"Прип|Притч|Екл|Піс|"
        r"Муд|Сир|"
        r"Іс|Єр|Плач|Вар|Єз|Дан|"
        r"Ос|Йоіл|Ам|Авд|Йона|Мих|"
        r"Наум|Авак|Соф|Аг|Зах|Мал|"
        r"[1-4]\s*Мак"

        r")"
    )

    REFERENCE_START_RE = re.compile(
        rf"(?<![А-ЯІЇЄҐа-яіїєґ])"
        rf"({BOOK_PATTERN})"
        rf"\.?\s*"
        rf"\d+"
        rf"\s*[,.:]"
        rf"\s*\d+",
        re.IGNORECASE,
    )

    GOSPEL_BOOKS = {
        "мт",
        "мф",
        "мк",
        "мр",
        "лк",
        "лук",
        "ів",
        "ин",
        "йо",
    }

    APOSTLE_BOOKS = {
        "діян",
        "дії",
        "рм",
        "рим",
        "кр",
        "кор",
        "гал",
        "еф",
        "фл",
        "флп",
        "кл",
        "кол",
        "сол",
        "тм",
        "тим",
        "тит",
        "флм",
        "євр",
        "як",
        "пт",
        "ів",
        "юд",
        "одкр",
    }

    def __init__(
        self,
        year: int = 2026,
        html_file: Path | None = None,
    ):
        self.year = year

        self.html_file = (
            html_file
            if html_file is not None
            else PROJECT_ROOT / "calendar.html"
        )

        self.database = ReadingsDatabase()

    def load_html(self) -> BeautifulSoup:
        if not self.html_file.exists():
            raise FileNotFoundError(
                f"Не знайдено HTML-файл календаря: {self.html_file}"
            )

        html = self.html_file.read_text(
            encoding="utf-8",
            errors="replace",
        )

        return BeautifulSoup(
            html,
            "html.parser",
        )

    def find_months(
        self,
        soup: BeautifulSoup,
    ) -> list[dict[str, Any]]:
        months: list[dict[str, Any]] = []

        for item in soup.select("[data-mounth]"):
            month_value = item.get("data-mounth")
            href_value = item.get("href")

            if month_value is None or href_value is None:
                continue

            try:
                month_number = int(
                    str(month_value).strip()
                )
            except ValueError:
                continue

            if not 1 <= month_number <= 12:
                continue

            href = str(href_value).strip().lstrip("#")

            if not href:
                continue

            months.append({
                "month": month_number,
                "href": href,
            })

        unique_months: dict[int, dict[str, Any]] = {}

        for month_info in months:
            unique_months[month_info["month"]] = month_info

        result = list(unique_months.values())
        result.sort(key=lambda item: item["month"])

        return result

    def find_month_block(
        self,
        soup: BeautifulSoup,
        href: str,
    ) -> Tag | None:
        block = soup.find(id=href)

        if isinstance(block, Tag):
            return block

        return None

    def find_days(
        self,
        month_block: Tag | None,
    ) -> list[Tag]:
        if month_block is None:
            return []

        table = month_block.find(
            "table",
            class_="e-cal-table",
        )

        if not isinstance(table, Tag):
            return []

        tbody = table.find("tbody")

        if not isinstance(tbody, Tag):
            return []

        rows = tbody.find_all(
            "tr",
            recursive=False,
        )

        return [
            row
            for row in rows
            if isinstance(row, Tag)
        ]

    @staticmethod
    def normalize_text(value: str) -> str:
        value = value.replace("\xa0", " ")
        value = value.replace("—", "–")

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    def get_readings_text(
        self,
        small: Tag | None,
    ) -> str:
        if small is None:
            return ""

        parts: list[str] = []

        for child in small.children:
            if isinstance(child, Tag):
                if child.name == "br":
                    parts.append("\n")

                elif child.name == "b":
                    text = child.get_text(
                        " ",
                        strip=True,
                    )

                    if text:
                        parts.append(f"\n{text} ")

                else:
                    text = child.get_text(
                        " ",
                        strip=True,
                    )

                    if text:
                        parts.append(text)

            else:
                text = str(child)

                if text.strip():
                    parts.append(text)

        text = "".join(parts)

        text = text.replace("\xa0", " ")
        text = text.replace("\r", "\n")

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r"\n+",
            "\n",
            text,
        )

        return text.strip()

    def extract_references(
        self,
        small: Tag | None,
    ) -> list[str]:
        text = self.get_readings_text(small)

        if not text:
            return []

        references: list[str] = []

        for line in text.splitlines():
            line = self.normalize_text(line)

            if not line:
                continue

            line_references = self.extract_references_from_line(
                line
            )

            for reference in line_references:
                if reference not in references:
                    references.append(reference)

        return references

    def extract_references_from_line(
        self,
        line: str,
    ) -> list[str]:
        references: list[str] = []

        matches = list(
            self.REFERENCE_START_RE.finditer(line)
        )

        if not matches:
            return references

        for index, match in enumerate(matches):
            start = match.start()

            if index + 1 < len(matches):
                end = matches[index + 1].start()
            else:
                end = len(line)

            raw_reference = line[start:end]

            reference = self.clean_reference(
                raw_reference
            )

            if reference:
                references.append(reference)

        return references

    def clean_reference(
        self,
        reference: str,
    ) -> str:
        reference = self.normalize_text(reference)

        reference = re.split(
            r"\s+(?:"
            r"Об|Св|Ап|Єв|"
            r"Апостол|Євангеліє"
            r")\s*[:.]",
            reference,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        reference = re.split(
            r"\s+(?:"
            r"Ап\.?\s+до|"
            r"Єв\.?\s+[А-ЯІЇЄҐа-яіїєґ]+|"
            r"Апостол\s+до|"
            r"Євангеліє\s+від"
            r")",
            reference,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        reference = re.split(
            r"\s+(?:"
            r"ряд\.|"
            r"та\s+святого|"
            r"святого\s+[-–]|"
            r"на\s+утрені|"
            r"на\s+Літургії|"
            r"на\s+вечірні|"
            r"на\s+часах"
            r")",
            reference,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        reference = reference.strip()

        # Видаляємо:
        # (зач. 229)
        # (зач.229)
        # зач. 229
        # (зач. 229
        reference = re.sub(
            r"\s*\(?\s*зач\.?\s*\d+\s*\)?",
            "",
            reference,
            flags=re.IGNORECASE,
        )

        reference = reference.strip()

        # Прибираємо початкову зовнішню дужку.
        reference = reference.lstrip("( ").strip()

        # Прибираємо зайву кінцеву дужку,
        # навіть якщо після неї стоять крапка, кома або крапка з комою.
        reference = re.sub(
            r"[\s.;,]*\)+[\s.;,]*$",
            "",
            reference,
        ).strip()

        # Додаткова перевірка на випадок кількох дужок.
        while reference.endswith(")"):
            reference = reference[:-1].rstrip(" .;,")

        reference = reference.rstrip(" .;,")

        reference = re.sub(
            r"^([1-4]?\s*[А-ЯІЇЄҐа-яіїєґ]+)"
            r"\s*\.\s*",
            r"\1. ",
            reference,
        )

        reference = re.sub(
            r"^([1-4]?\s*[А-ЯІЇЄҐа-яіїєґ]+)"
            r"\s+(?=\d)",
            r"\1. ",
            reference,
        )

        reference = re.sub(
            r"\s*,\s*",
            ",",
            reference,
        )

        reference = re.sub(
            r"\s*;\s*",
            ";",
            reference,
        )

        reference = re.sub(
            r"\s*:\s*",
            ":",
            reference,
        )

        reference = re.sub(
            r"\s*[-–]\s*",
            "-",
            reference,
        )

        reference = re.sub(
            r"\s+",
            " ",
            reference,
        )

        # Фінальне очищення кінця рядка.
        reference = re.sub(
            r"\)+(?=[\s.;,]*$)",
            "",
            reference,
        )

        reference = reference.rstrip(" .;,")
        reference = reference.strip()

        return reference

    def get_book_abbreviation(
        self,
        reference: str,
    ) -> str:
        reference = self.normalize_text(reference)

        reference = re.sub(
            r"^[1-4]\s*",
            "",
            reference,
        )

        match = re.match(
            r"([А-ЯІЇЄҐа-яіїєґ]+)",
            reference,
        )

        if match is None:
            return ""

        return match.group(1).lower().strip()

    def detect_reading_type(
        self,
        reference: str,
    ) -> int:
        book = self.get_book_abbreviation(
            reference
        )

        if book in self.GOSPEL_BOOKS:
            return GOSPEL

        if book in self.APOSTLE_BOOKS:
            return APOSTLE

        return OLD_TESTAMENT

    def normalize_day_readings(
        self,
        references: list[str],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        positions = {
            APOSTLE: 0,
            GOSPEL: 0,
            OLD_TESTAMENT: 0,
        }

        for reference in references:
            reading_type = self.detect_reading_type(
                reference
            )

            positions[reading_type] += 1

            normalized.append({
                "reading_type": reading_type,
                "reference": reference,
                "position": positions[reading_type],
            })

        return normalized

    def parse_day(
        self,
        day_row: Tag,
        month_number: int,
    ) -> dict[str, Any] | None:
        cells = day_row.find_all(
            "td",
            recursive=False,
        )

        if len(cells) < 3:
            return None

        day_text = cells[0].get_text(
            " ",
            strip=True,
        )

        weekday = cells[1].get_text(
            " ",
            strip=True,
        )

        try:
            day_number = int(
                self.normalize_text(day_text)
            )
        except ValueError:
            return None

        try:
            calendar_date = date(
                self.year,
                month_number,
                day_number,
            )
        except ValueError:
            return None

        content_cell = cells[2]

        paragraphs = content_cell.find_all(
            "p",
            recursive=False,
        )

        title = ""

        if paragraphs:
            title = self.normalize_text(
                paragraphs[0].get_text(
                    " ",
                    strip=True,
                )
            )

        small = content_cell.find("small")

        if not isinstance(small, Tag):
            small = None

        references = self.extract_references(
            small
        )

        readings = self.normalize_day_readings(
            references
        )

        return {
            "date": calendar_date.isoformat(),
            "year": self.year,
            "month": month_number,
            "day": day_number,
            "weekday": self.normalize_text(weekday),
            "title": title,
            "references": references,
            "readings": readings,
        }

    def parse_month(
        self,
        soup: BeautifulSoup,
        month_info: dict[str, Any],
    ) -> list[dict[str, Any]]:
        month_number = month_info["month"]
        href = month_info["href"]

        month_block = self.find_month_block(
            soup,
            href,
        )

        if month_block is None:
            print(
                f"❌ Не знайдено блок місяця "
                f"{month_number:02d}: {href}"
            )

            return []

        day_rows = self.find_days(
            month_block
        )

        parsed_days: list[dict[str, Any]] = []

        for day_row in day_rows:
            parsed_day = self.parse_day(
                day_row,
                month_number,
            )

            if parsed_day is not None:
                parsed_days.append(parsed_day)

        parsed_days.sort(
            key=lambda item: item["date"]
        )

        return parsed_days

    def parse_year(
        self,
    ) -> list[dict[str, Any]]:
        soup = self.load_html()
        months = self.find_months(soup)

        if len(months) != 12:
            print(
                f"⚠️ Знайдено місяців: "
                f"{len(months)}. Очікувалося 12."
            )

        calendar_days: list[dict[str, Any]] = []

        for month_info in months:
            month_days = self.parse_month(
                soup,
                month_info,
            )

            calendar_days.extend(month_days)

            readings_count = sum(
                len(day["readings"])
                for day in month_days
            )

            empty_count = sum(
                1
                for day in month_days
                if not day["readings"]
            )

            print(
                f"Місяць {month_info['month']:02d}: "
                f"{len(month_days)} днів, "
                f"{readings_count} читань, "
                f"без читань: {empty_count}"
            )

        calendar_days.sort(
            key=lambda item: item["date"]
        )

        return calendar_days

    def save_day(
        self,
        day_data: dict[str, Any],
    ) -> int:
        calendar_date = day_data["date"]
        readings = day_data["readings"]

        self.database.delete_date(
            calendar_date
        )

        saved_count = 0

        for reading in readings:
            self.database.save(
                date=calendar_date,
                reading_type=reading["reading_type"],
                reference=reading["reference"],
                position=reading["position"],
            )

            saved_count += 1

        return saved_count

    def import_year(
        self,
    ) -> dict[str, Any]:
        calendar_days = self.parse_year()

        if not calendar_days:
            raise RuntimeError(
                "Не вдалося розібрати календар."
            )

        expected_days = (
            date(self.year + 1, 1, 1)
            - date(self.year, 1, 1)
        ).days

        if len(calendar_days) != expected_days:
            raise RuntimeError(
                f"Кількість днів неправильна. "
                f"Очікувалося: {expected_days}, "
                f"отримано: {len(calendar_days)}."
            )

        saved_readings = 0
        days_without_readings: list[str] = []
        errors: list[str] = []

        for day_data in calendar_days:
            calendar_date = day_data["date"]

            try:
                saved_for_day = self.save_day(
                    day_data
                )

                saved_readings += saved_for_day

                if saved_for_day == 0:
                    days_without_readings.append(
                        calendar_date
                    )

            except Exception as error:
                errors.append(
                    f"{calendar_date}: {error}"
                )

        return {
            "days_processed": len(calendar_days),
            "readings_saved": saved_readings,
            "days_without_readings": days_without_readings,
            "errors": errors,
            "database_count": self.database.count(),
        }


def reading_type_name(
    reading_type: int,
) -> str:
    if reading_type == APOSTLE:
        return "Апостол"

    if reading_type == GOSPEL:
        return "Євангеліє"

    if reading_type == OLD_TESTAMENT:
        return "Старий Завіт"

    return f"Невідомий тип {reading_type}"


def print_database_day(
    database: ReadingsDatabase,
    calendar_date: str,
) -> None:
    rows = database.get(calendar_date)

    print()
    print(f"Перевірка дати: {calendar_date}")

    if not rows:
        print("  Читань у базі немає.")
        return

    for row in rows:
        print(
            f"  {reading_type_name(row['reading_type'])}, "
            f"позиція {row['position']}: "
            f"{row['reference']}"
        )


def main() -> None:
    print("=" * 50)
    print("MGCE CALENDAR IMPORT")
    print("=" * 50)
    print()

    importer = MgceImporter(
        year=2026
    )

    try:
        result = importer.import_year()

    except Exception as error:
        print()
        print(f"❌ Імпорт зупинено: {error}")
        return

    print()
    print("=" * 50)
    print("IMPORT FINISHED")
    print("=" * 50)

    print(
        f"Days processed: "
        f"{result['days_processed']}"
    )

    print(
        f"Readings saved: "
        f"{result['readings_saved']}"
    )

    print(
        f"Database records: "
        f"{result['database_count']}"
    )

    print(
        f"Days without readings: "
        f"{len(result['days_without_readings'])}"
    )

    print(
        f"Errors: "
        f"{len(result['errors'])}"
    )

    if result["days_without_readings"]:
        print()
        print("Дні без читань:")

        for calendar_date in result["days_without_readings"]:
            print(f"  - {calendar_date}")

    if result["errors"]:
        print()
        print("Помилки:")

        for error in result["errors"]:
            print(f"  - {error}")

    print_database_day(
        importer.database,
        "2026-01-01",
    )

    print_database_day(
        importer.database,
        "2026-02-16",
    )

    print_database_day(
        importer.database,
        "2026-03-02",
    )

    print_database_day(
        importer.database,
        "2026-10-01",
    )

    print_database_day(
        importer.database,
        "2026-10-31",
    )

    print_database_day(
        importer.database,
        "2026-12-31",
    )


if __name__ == "__main__":
    main()