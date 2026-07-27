"""Універсальний парсер біблійних посилань для GodSearchBot.

Підтримує формати з readings.db, зокрема:

    Мт. 5,1-12
    Ів. 15,17-16,2
    Лк. 10,38-42;11,27-28
    2 Тм. 1,1-2.8-18
    Євр. 11,9-10.17-23.32-40
    Мт. 18,18-22;19,1-2.13-15
    Лк. 1,1-25.57-68.76.80
    1 Тм. 5,1-10б
    Вих. 1,1-20;Йова 1,1-12

Крапка розділяє групи віршів, крапка з комою — окремі частини
посилання, а нова назва книги після крапки з комою змінює книгу.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


class ReferenceParseError(ValueError):
    """Посилання має непідтримуваний або пошкоджений формат."""


@dataclass(frozen=True, slots=True)
class Passage:
    """Один безперервний біблійний уривок."""

    book: str
    start_chapter: int
    start_verse: int
    end_chapter: int
    end_verse: int
    raw: str = ""

    @property
    def is_single_verse(self) -> bool:
        return (
            self.start_chapter == self.end_chapter
            and self.start_verse == self.end_verse
        )

    @property
    def crosses_chapter(self) -> bool:
        return self.start_chapter != self.end_chapter

    def compact(self) -> str:
        """Повертає нормалізований запис уривка."""
        if self.is_single_verse:
            return f"{self.book}. {self.start_chapter},{self.start_verse}"

        if self.start_chapter == self.end_chapter:
            return (
                f"{self.book}. {self.start_chapter},"
                f"{self.start_verse}-{self.end_verse}"
            )

        return (
            f"{self.book}. {self.start_chapter},{self.start_verse}-"
            f"{self.end_chapter},{self.end_verse}"
        )


@dataclass(frozen=True, slots=True)
class ParsedReference:
    original: str
    normalized: str
    passages: tuple[Passage, ...]

    def __iter__(self):
        return iter(self.passages)

    def __len__(self) -> int:
        return len(self.passages)


class ReferenceParser:
    """Розбирає церковні біблійні посилання на окремі уривки."""

    _DASHES_RE = re.compile(r"[‐‑‒–—―−]")
    _SPACES_RE = re.compile(r"\s+")
    _BOOK_AT_START_RE = re.compile(
        r"^\s*(?P<book>(?:[1-4]\s*)?[А-ЯІЇЄҐа-яіїєґ]+"
        r"(?:\s+[А-ЯІЇЄҐа-яіїєґ]+)*)\.?\s*(?P<body>\d.*)$"
    )
    _CHAPTER_AND_TAIL_RE = re.compile(
        r"^(?P<chapter>\d+)\s*,\s*(?P<tail>.+)$"
    )
    _VERSE_RE = re.compile(r"^(?P<number>\d+)(?P<suffix>[а-яіїєґ]?)$")
    _RANGE_RE = re.compile(
        r"^(?P<start>\d+[а-яіїєґ]?)\s*-\s*"
        r"(?:(?P<end_chapter>\d+)\s*,\s*)?"
        r"(?P<end>\d+[а-яіїєґ]?)$"
    )

    _BOOK_ALIASES = {
        "1 Кр": "1 Кор",
        "2 Кр": "2 Кор",
    }

    _TRAILING_SERVICE_TEXT_RE = re.compile(
        r"^(?P<reference>.+?)\)\s*та\s+Отців(?:-|\s).*",
        re.IGNORECASE,
    )

    @classmethod
    def normalize(cls, reference: str) -> str:
        if not isinstance(reference, str):
            raise TypeError("Біблійне посилання повинно бути рядком.")

        value = reference.replace("\xa0", " ")
        value = cls._DASHES_RE.sub("-", value)
        value = cls._SPACES_RE.sub(" ", value).strip()

        service_match = cls._TRAILING_SERVICE_TEXT_RE.match(value)
        if service_match:
            value = service_match.group("reference").strip()

        value = value.strip("() ")
        value = re.sub(r"\s*([,;.])\s*", r"\1", value)
        value = re.sub(r"\s*-\s*", "-", value)

        if not value:
            raise ReferenceParseError("Отримано порожнє посилання.")

        return value

    @classmethod
    def parse(cls, reference: str) -> ParsedReference:
        normalized = cls.normalize(reference)

        clauses = normalized.split(";")
        if any(not clause for clause in clauses):
            raise ReferenceParseError(
                f"Порожня частина біля ';' у посиланні: {reference!r}"
            )

        current_book: str | None = None
        passages: list[Passage] = []

        for clause in clauses:
            book, body = cls._extract_book(clause, current_book)
            current_book = book
            passages.extend(cls._parse_book_body(book, body, clause))

        if not passages:
            raise ReferenceParseError(
                f"Не знайдено жодного уривка: {reference!r}"
            )

        return ParsedReference(
            original=reference,
            normalized=normalized,
            passages=tuple(passages),
        )

    @classmethod
    def parse_passages(cls, reference: str) -> list[Passage]:
        """Сумісний короткий виклик для BibleService."""
        return list(cls.parse(reference).passages)

    @classmethod
    def _extract_book(
        cls,
        clause: str,
        inherited_book: str | None,
    ) -> tuple[str, str]:
        match = cls._BOOK_AT_START_RE.match(clause)

        if match:
            book = cls._normalize_book(match.group("book"))
            body = match.group("body")
            return book, body

        if inherited_book is None:
            raise ReferenceParseError(
                f"Не вдалося визначити книгу у частині: {clause!r}"
            )

        if not clause[0].isdigit():
            raise ReferenceParseError(
                f"Сторонній текст у частині посилання: {clause!r}"
            )

        return inherited_book, clause

    @classmethod
    def _normalize_book(cls, book: str) -> str:
        book = cls._SPACES_RE.sub(" ", book).strip()
        if not book:
            raise ReferenceParseError("Назва книги порожня.")
        return cls._BOOK_ALIASES.get(book, book)

    @classmethod
    def _parse_book_body(
        cls,
        book: str,
        body: str,
        raw_clause: str,
    ) -> list[Passage]:
        groups = body.split(".")
        if any(not group for group in groups):
            raise ReferenceParseError(
                f"Порожня частина біля '.' у: {raw_clause!r}"
            )

        first = cls._CHAPTER_AND_TAIL_RE.match(groups[0])
        if not first:
            raise ReferenceParseError(
                f"Очікував формат 'розділ,вірші' у: {raw_clause!r}"
            )

        current_chapter = int(first.group("chapter"))
        cls._validate_positive(current_chapter, "розділ", raw_clause)

        passages = cls._parse_verse_group(
            book=book,
            chapter=current_chapter,
            group=first.group("tail"),
            raw=groups[0],
        )

        for group in groups[1:]:
            chapter_match = cls._CHAPTER_AND_TAIL_RE.match(group)

            if chapter_match:
                current_chapter = int(chapter_match.group("chapter"))
                cls._validate_positive(
                    current_chapter,
                    "розділ",
                    raw_clause,
                )
                verse_group = chapter_match.group("tail")
            else:
                verse_group = group

            passages.extend(
                cls._parse_verse_group(
                    book=book,
                    chapter=current_chapter,
                    group=verse_group,
                    raw=group,
                )
            )

        return passages

    @classmethod
    def _parse_verse_group(
        cls,
        book: str,
        chapter: int,
        group: str,
        raw: str,
    ) -> list[Passage]:
        # Коми всередині цієї групи дозволені тільки в переході
        # між розділами: 17-16,2. Інші коми означають помилку.
        range_match = cls._RANGE_RE.match(group)
        if range_match:
            start_verse = cls._verse_number(
                range_match.group("start"),
                raw,
            )
            end_chapter = (
                int(range_match.group("end_chapter"))
                if range_match.group("end_chapter")
                else chapter
            )
            end_verse = cls._verse_number(
                range_match.group("end"),
                raw,
            )

            cls._validate_range(
                chapter,
                start_verse,
                end_chapter,
                end_verse,
                raw,
            )

            return [
                Passage(
                    book=book,
                    start_chapter=chapter,
                    start_verse=start_verse,
                    end_chapter=end_chapter,
                    end_verse=end_verse,
                    raw=raw,
                )
            ]

        verse_match = cls._VERSE_RE.match(group)
        if verse_match:
            verse = cls._verse_number(group, raw)
            return [
                Passage(
                    book=book,
                    start_chapter=chapter,
                    start_verse=verse,
                    end_chapter=chapter,
                    end_verse=verse,
                    raw=raw,
                )
            ]

        raise ReferenceParseError(
            f"Не вдалося розпізнати групу віршів {group!r} "
            f"для книги {book!r}, розділ {chapter}."
        )

    @classmethod
    def _verse_number(cls, token: str, raw: str) -> int:
        match = cls._VERSE_RE.match(token)
        if not match:
            raise ReferenceParseError(
                f"Некоректний номер вірша {token!r} у {raw!r}"
            )

        number = int(match.group("number"))
        cls._validate_positive(number, "вірш", raw)
        return number

    @staticmethod
    def _validate_positive(
        number: int,
        label: str,
        raw: str,
    ) -> None:
        if number <= 0:
            raise ReferenceParseError(
                f"{label.capitalize()} повинен бути більшим за 0 "
                f"у {raw!r}."
            )

    @classmethod
    def _validate_range(
        cls,
        start_chapter: int,
        start_verse: int,
        end_chapter: int,
        end_verse: int,
        raw: str,
    ) -> None:
        cls._validate_positive(end_chapter, "кінцевий розділ", raw)
        cls._validate_positive(end_verse, "кінцевий вірш", raw)

        if end_chapter < start_chapter:
            raise ReferenceParseError(
                f"Кінцевий розділ менший за початковий у {raw!r}."
            )

        if (
            end_chapter == start_chapter
            and end_verse < start_verse
        ):
            raise ReferenceParseError(
                f"Кінцевий вірш менший за початковий у {raw!r}."
            )


def parse_reference(reference: str) -> list[Passage]:
    """Функціональний API для простого імпорту в BibleService."""
    return ReferenceParser.parse_passages(reference)


def format_passages(passages: Iterable[Passage]) -> str:
    """Допоміжне представлення для логів і тестів."""
    return "; ".join(passage.compact() for passage in passages)
