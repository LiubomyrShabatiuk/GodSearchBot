"""Download the HOM translation from Bolls API and build database/bible.db."""

from __future__ import annotations

import argparse
import html
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://bolls.life"
TRANSLATION = "HOM"
DEFAULT_DB = Path(__file__).resolve().parent / "database" / "bible.db"


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def request_json(session: requests.Session, url: str, retries: int = 4) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt == retries:
                break
            delay = min(2 ** (attempt - 1), 8)
            print(f"Помилка запиту. Повтор через {delay} с: {error}")
            time.sleep(delay)
    raise RuntimeError(f"Не вдалося отримати {url}: {last_error}")


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            chapters INTEGER NOT NULL,
            translation TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS verses (
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (book_id, chapter, verse),
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        );

        CREATE INDEX IF NOT EXISTS idx_verses_lookup
            ON verses(book_id, chapter, verse);
        """
    )


def normalize_books(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("books", "data", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise RuntimeError("API повернув невідомий формат списку книг.")

    books: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        book_id = item.get("bookid", item.get("book_id", item.get("id")))
        name = item.get("name")
        chapters = item.get("chapters")
        try:
            book_id = int(book_id)
            chapters = int(chapters)
        except (TypeError, ValueError):
            continue
        if name and chapters > 0:
            books.append({"book_id": book_id, "name": str(name), "chapters": chapters})
    if not books:
        raise RuntimeError("У відповіді API не знайдено жодної книги.")
    return books


def normalize_verses(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("verses", "data", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise RuntimeError("API повернув невідомий формат розділу.")

    verses: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        number = item.get("verse", item.get("verse_number"))
        try:
            number = int(number)
        except (TypeError, ValueError):
            continue
        text = clean_text(str(item.get("text", "")))
        if text:
            verses.append({"verse": number, "text": text})
    return verses


def import_bible(db_path: Path, resume: bool = True) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "GodSearchBot/2.0",
        "Accept": "application/json",
    })

    print("Завантажую список книг…")
    books_payload = request_json(session, f"{API_BASE}/get-books/{TRANSLATION}/")
    books = normalize_books(books_payload)

    connection = sqlite3.connect(db_path)
    try:
        create_schema(connection)
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            ("translation", TRANSLATION),
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, datetime('now'))",
            ("imported_at",),
        )

        total_verses = connection.execute("SELECT COUNT(*) FROM verses").fetchone()[0]

        for book_index, book in enumerate(books, start=1):
            connection.execute(
                "INSERT OR REPLACE INTO books(book_id, name, chapters, translation) VALUES (?, ?, ?, ?)",
                (book["book_id"], book["name"], book["chapters"], TRANSLATION),
            )
            connection.commit()

            print(f"[{book_index}/{len(books)}] {book['name']}")
            for chapter in range(1, book["chapters"] + 1):
                if resume:
                    exists = connection.execute(
                        "SELECT 1 FROM verses WHERE book_id=? AND chapter=? LIMIT 1",
                        (book["book_id"], chapter),
                    ).fetchone()
                    if exists:
                        print(f"  розділ {chapter}: вже імпортовано")
                        continue

                url = (
                    f"{API_BASE}/get-text/{TRANSLATION}/"
                    f"{book['book_id']}/{chapter}/"
                )
                verses = normalize_verses(request_json(session, url))
                if not verses:
                    raise RuntimeError(
                        f"Порожній розділ: {book['name']} {chapter}"
                    )

                connection.executemany(
                    "INSERT OR REPLACE INTO verses(book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
                    [
                        (book["book_id"], chapter, item["verse"], item["text"])
                        for item in verses
                    ],
                )
                connection.commit()
                total_verses += len(verses)
                print(f"  розділ {chapter}: {len(verses)} віршів")
                time.sleep(0.05)

        print("\nIMPORT FINISHED")
        print(f"Books: {len(books)}")
        print(f"Verses in database: {connection.execute('SELECT COUNT(*) FROM verses').fetchone()[0]}")
        print(f"Database: {db_path}")
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Створення локальної bible.db")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Очистити стару базу й почати імпорт заново",
    )
    args = parser.parse_args()

    if args.restart and args.db.exists():
        args.db.unlink()

    try:
        import_bible(args.db, resume=not args.restart)
    except KeyboardInterrupt:
        print("\nІмпорт зупинено. Повторний запуск продовжить роботу.")
        return 130
    except Exception as error:
        print(f"\nПОМИЛКА: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
