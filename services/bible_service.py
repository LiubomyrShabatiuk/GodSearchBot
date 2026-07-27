"""Local Bible service backed by database/bible.db."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

try:
    from .reference_parser import ReferenceParseError, ReferenceParser
except ImportError:
    from reference_parser import ReferenceParseError, ReferenceParser


@dataclass(frozen=True)
class PassagePart:
    book_alias: str
    chapter_start: int
    verse_start: int
    chapter_end: int
    verse_end: int


class BibleService:
    DEFAULT_DB = Path(__file__).resolve().parents[1] / "database" / "bible.db"


    # Стабільні номери книг у Bolls. Використовуються першими,
    # тому робота сервісу не залежить від повної назви книги в bible.db.
    BOOK_IDS = {
        "Мт": 40,
        "Мф": 40,
        "Мк": 41,
        "Мр": 41,
        "Лк": 42,
        "Лук": 42,
        "Ів": 43,
        "Ин": 43,
        "Йо": 43,
        "Діян": 44,
        "Дії": 44,
        "Рим": 45,
        "Рм": 45,
        "1 Кор": 46,
        "2 Кор": 47,
        "1 Кр": 46,
        "2 Кр": 47,
        "Гал": 48,
        "Еф": 49,
        "Флп": 50,
        "Фл": 50,
        "Кол": 51,
        "Кл": 51,
        "1 Сол": 52,
        "2 Сол": 53,
        "1 Тим": 54,
        "1 Тм": 54,
        "2 Тим": 55,
        "2 Тм": 55,
        "Тит": 56,
        "Флм": 57,
        "Євр": 58,
        "Як": 59,
        "1 Пт": 60,
        "2 Пт": 61,
        "1 Ів": 62,
        "2 Ів": 63,
        "3 Ів": 64,
        "Юд": 65,
        "Одкр": 66,
    }

    BOOK_ALIASES = {
        "Бут": ("Буття",), "Вих": ("Вихід",), "Лев": ("Левит",),
        "Чис": ("Числа",), "Втор": ("Повторення Закону", "Второзаконня"),
        "Нав": ("Ісус Навин",), "Суд": ("Суддів",), "Рут": ("Рут",),
        "1 Цар": ("1 Самуїла", "1 Царів"), "2 Цар": ("2 Самуїла", "2 Царів"),
        "3 Цар": ("1 Царів", "3 Царів"), "4 Цар": ("2 Царів", "4 Царів"),
        "1 Хр": ("1 Хронік",), "2 Хр": ("2 Хронік",), "Езд": ("Ездри",),
        "Неєм": ("Неємії",), "Тов": ("Товита",), "Юдит": ("Юдити",),
        "Ест": ("Естери",), "Йов": ("Іов", "Йова"), "Йова": ("Іов", "Йова"), "Пс": ("Псалми", "Псалом"),
        "Прип": ("Приповідки", "Приповістей"), "Екл": ("Екклезіаста", "Проповідника"),
        "Пісн": ("Пісня над піснями", "Пісні Пісень"),
        "Муд": ("Мудрості", "Премудрості"), "Сир": ("Сираха",),
        "Іс": ("Ісаї",), "Єр": ("Єремії",), "Плач": ("Плач Єремії",),
        "Вар": ("Варуха",), "Єз": ("Єзекіїла",), "Дан": ("Даниїла",),
        "Ос": ("Осії",), "Йоіл": ("Йоїла",), "Ам": ("Амоса",),
        "Авд": ("Авдія",), "Йона": ("Йони",), "Мих": ("Михея",),
        "Наум": ("Наума",), "Ав": ("Авакума",), "Соф": ("Софонії",),
        "Аг": ("Аггея",), "Зах": ("Захарії",), "Мал": ("Малахії",),
        "Мт": ("Матей", "Від Матея", "Матея"),
        "Мф": ("Матей", "Від Матея", "Матея"),
        "Мк": ("Марко", "Від Марка", "Марка"),
        "Мр": ("Марко", "Від Марка", "Марка"),
        "Лк": ("Лука", "Від Луки", "Луки"),
        "Лук": ("Лука", "Від Луки", "Луки"),
        "Ів": ("Іван", "Від Івана", "Івана"),
        "Ин": ("Іван", "Від Івана", "Івана"),
        "Йо": ("Іван", "Від Івана", "Івана"),
        "Діян": ("Дії", "Діяння", "Діяння Апостолів"),
        "Дії": ("Дії", "Діяння", "Діяння Апостолів"),
        "Рим": ("До Римлян", "Римлян"),
        "Рм": ("До римлян", "До Римлян", "Римлян"),
        "1 Кор": ("1 До Коринтян", "1 Коринтян"),
        "2 Кор": ("2 До Коринтян", "2 Коринтян"),
        "1 Кр": ("1 До Коринтян", "1 Коринтян"),
        "2 Кр": ("2 До Коринтян", "2 Коринтян"),
        "Гал": ("До Галатів", "Галатів"), "Еф": ("До Ефесян", "Ефесян"),
        "Флп": ("До Филип'ян", "До Филип’ян", "Филип'ян", "Филип’ян"),
        "Фл": ("До Филип'ян", "До Филип’ян", "Филип'ян", "Филип’ян"),
        "Кол": ("До Колосян", "Колосян"),
        "Кл": ("До Колосян", "Колосян"),
        "1 Сол": ("1 До Солунян", "1 Солунян"),
        "2 Сол": ("2 До Солунян", "2 Солунян"),
        "1 Тим": ("1 До Тимотея", "1 Тимотея"),
        "1 Тм": ("I до Тимотея", "1 До Тимотея", "1 Тимотея"),
        "2 Тим": ("2 До Тимотея", "2 Тимотея"),
        "2 Тм": ("II до Тимотея", "2 До Тимотея", "2 Тимотея"),
        "Тит": ("До Тита", "Тита"), "Флм": ("До Филимона", "Филимона"),
        "Євр": ("До Євреїв", "Євреїв"), "Як": ("Якова",),
        "1 Пт": ("1 Петра",), "2 Пт": ("2 Петра",),
        "1 Ів": ("1 Івана",), "2 Ів": ("2 Івана",), "3 Ів": ("3 Івана",),
        "Юд": ("Юди",), "Одкр": ("Об'явлення", "Об’явлення", "Одкровення"),
    }

    PART_PATTERN = re.compile(
        r"^(?P<chapter>\d+)\s*[,.:]\s*(?P<verse>\d+)"
        r"(?:\s*[-–—]\s*(?:(?P<end_chapter>\d+)\s*[,.:]\s*)?"
        r"(?P<end_verse>\d+))?$"
    )

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB

    @staticmethod
    def _norm(value: str) -> str:
        value = value.replace("’", "'").replace("`", "'")
        value = value.replace(".", " ")
        return re.sub(r"\s+", " ", value).strip().casefold()

    @staticmethod
    def _normalize_alias(value: str) -> str:
        value = value.strip().replace(".", "")
        value = re.sub(r"^([1-4])(?=[А-ЯІЇЄҐа-яіїєґ])", r"\1 ", value)
        return re.sub(r"\s+", " ", value)

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Не знайдено {self.db_path}. Запустіть: python import_bible.py"
            )
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _book_id(self, alias: str) -> int:
        normalized_alias = self._normalize_alias(alias)

        # Для книг Нового Завіту використовуємо стабільний book_id.
        direct_book_id = self.BOOK_IDS.get(normalized_alias)
        if direct_book_id is not None:
            with self._connect() as connection:
                exists = connection.execute(
                    "SELECT 1 FROM books WHERE book_id=? LIMIT 1",
                    (direct_book_id,),
                ).fetchone()
            if exists:
                return direct_book_id

        # Для решти книг залишається пошук за назвою.
        candidates = self.BOOK_ALIASES.get(normalized_alias)
        if not candidates:
            raise ValueError(f"Невідома біблійна книга: {alias}")

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT book_id, name FROM books"
            ).fetchall()

        normalized_rows = [
            (row["book_id"], self._norm(row["name"]))
            for row in rows
        ]

        for candidate in candidates:
            target = self._norm(candidate)
            for book_id, name in normalized_rows:
                if name == target:
                    return int(book_id)

        for candidate in candidates:
            target = self._norm(candidate)
            for book_id, name in normalized_rows:
                if target in name or name in target:
                    return int(book_id)

        available = ", ".join(
            str(row["name"]) for row in rows
        )
        raise ValueError(
            f"Книгу «{alias}» не знайдено у bible.db. "
            f"Доступні назви: {available}"
        )

    @classmethod
    def parse_reference(cls, reference: str) -> list[PassagePart]:
        """Розбирає посилання через універсальний ReferenceParser."""
        try:
            parsed = ReferenceParser.parse(reference)
        except ReferenceParseError as error:
            raise ValueError(
                f"Не вдалося розпізнати посилання «{reference}»: {error}"
            ) from error

        return [
            PassagePart(
                book_alias=cls._normalize_alias(passage.book),
                chapter_start=passage.start_chapter,
                verse_start=passage.start_verse,
                chapter_end=passage.end_chapter,
                verse_end=passage.end_verse,
            )
            for passage in parsed.passages
        ]

    def get_passage(self, reference: str) -> str:
        lines: list[str] = []
        for part in self.parse_reference(reference):
            book_id = self._book_id(part.book_alias)
            with self._connect() as connection:
                for chapter in range(part.chapter_start, part.chapter_end + 1):
                    start = part.verse_start if chapter == part.chapter_start else 1
                    end = part.verse_end if chapter == part.chapter_end else 999
                    rows = connection.execute(
                        """
                        SELECT chapter, verse, text FROM verses
                        WHERE book_id=? AND chapter=? AND verse BETWEEN ? AND ?
                        ORDER BY verse
                        """,
                        (book_id, chapter, start, end),
                    ).fetchall()
                    for row in rows:
                        prefix = (
                            f"{row['chapter']}:{row['verse']}"
                            if part.chapter_start != part.chapter_end
                            else str(row["verse"])
                        )
                        lines.append(f"{prefix}. {row['text']}")

        if not lines:
            raise LookupError(f"Текст для «{reference}» не знайдено")
        return "\n".join(lines)

    def format_passage(self, reference: str) -> str:
        return f"📜 {reference}\n\n{self.get_passage(reference)}"
