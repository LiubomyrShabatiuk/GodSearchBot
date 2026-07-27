"""Локальний пошук слів і фраз у тексті Біблії."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchResult:
    book_id: int
    book_name: str
    chapter: int
    verse: int
    text: str

    @property
    def reference(self) -> str:
        return f"{self.book_name} {self.chapter}:{self.verse}"


@dataclass(frozen=True)
class SearchPage:
    query: str
    results: list[SearchResult]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


class BibleSearchService:
    """Шукає довільні слова та фрази в таблиці verses."""

    DEFAULT_DB = Path(__file__).resolve().parents[1] / "database" / "bible.db"
    MIN_QUERY_LENGTH = 2
    MAX_QUERY_LENGTH = 100
    DEFAULT_PAGE_SIZE = 6
    MAX_PAGE_SIZE = 20

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Не знайдено базу Біблії: {self.db_path}")
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @classmethod
    def normalize_query(cls, query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("Пошуковий запит має бути рядком.")

        normalized = re.sub(r"\s+", " ", query).strip()
        if len(normalized) < cls.MIN_QUERY_LENGTH:
            raise ValueError("Введіть щонайменше 2 символи для пошуку.")
        if len(normalized) > cls.MAX_QUERY_LENGTH:
            raise ValueError(
                f"Пошуковий запит не може перевищувати {cls.MAX_QUERY_LENGTH} символів."
            )
        return normalized

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @classmethod
    def _search_terms(cls, query: str) -> list[str]:
        # Прибираємо просту пунктуацію, але залишаємо українські літери та апостроф.
        terms = re.findall(r"[\wА-ЯІЇЄҐа-яіїєґ'’]+", query, flags=re.UNICODE)
        return [term for term in terms if term]

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> SearchResult:
        return SearchResult(
            book_id=int(row["book_id"]),
            book_name=str(row["book_name"]),
            chapter=int(row["chapter"]),
            verse=int(row["verse"]),
            text=str(row["text"]),
        )

    def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> SearchPage:
        normalized = self.normalize_query(query)

        if not isinstance(page, int) or page < 1:
            raise ValueError("Номер сторінки має бути цілим числом від 1.")
        if not isinstance(page_size, int) or not 1 <= page_size <= self.MAX_PAGE_SIZE:
            raise ValueError(
                f"Кількість результатів має бути від 1 до {self.MAX_PAGE_SIZE}."
            )

        terms = self._search_terms(normalized)
        if not terms:
            raise ValueError("Запит не містить слів для пошуку.")

        # Спочатку шукаємо точну фразу. Якщо її немає — вірші,
        # у яких присутні всі слова запиту незалежно від їхнього порядку.
        phrase_pattern = f"%{self._escape_like(normalized)}%"
        phrase_where = "LOWER(v.text) LIKE LOWER(?) ESCAPE '\\'"
        phrase_params: list[str] = [phrase_pattern]

        with self._connect() as connection:
            phrase_total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM verses v WHERE {phrase_where}",
                    phrase_params,
                ).fetchone()[0]
            )

            if phrase_total > 0:
                where_sql = phrase_where
                params = phrase_params
                total = phrase_total
            else:
                clauses = ["LOWER(v.text) LIKE LOWER(?) ESCAPE '\\'" for _ in terms]
                where_sql = " AND ".join(clauses)
                params = [f"%{self._escape_like(term)}%" for term in terms]
                total = int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM verses v WHERE {where_sql}",
                        params,
                    ).fetchone()[0]
                )

            total_pages = (total + page_size - 1) // page_size if total else 0
            effective_page = min(page, total_pages) if total_pages else 1
            offset = (effective_page - 1) * page_size

            rows = connection.execute(
                f"""
                SELECT
                    v.book_id,
                    b.name AS book_name,
                    v.chapter,
                    v.verse,
                    v.text
                FROM verses v
                JOIN books b ON b.book_id = v.book_id
                WHERE {where_sql}
                ORDER BY v.book_id, v.chapter, v.verse
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return SearchPage(
            query=normalized,
            results=[self._row_to_result(row) for row in rows],
            total=total,
            page=effective_page,
            page_size=page_size,
        )

    @staticmethod
    def format_page(search_page: SearchPage) -> str:
        if not search_page.results:
            return (
                f"🔎 За запитом «{search_page.query}» нічого не знайдено.\n\n"
                "Спробуйте інше слово, його частину або коротшу фразу."
            )

        lines = [
            f"🔎 Пошук: «{search_page.query}»",
            f"Знайдено віршів: {search_page.total}",
            "",
        ]

        start_number = (search_page.page - 1) * search_page.page_size
        for position, result in enumerate(search_page.results, start=start_number + 1):
            lines.extend(
                [
                    f"{position}. 📖 {result.reference}",
                    (result.text if len(result.text) <= 500 else result.text[:497].rstrip() + "…"),
                    "",
                ]
            )

        lines.append(
            f"Сторінка {search_page.page} із {search_page.total_pages}"
        )
        return "\n".join(lines).strip()
