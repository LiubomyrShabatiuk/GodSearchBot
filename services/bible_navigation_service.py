import sqlite3
from pathlib import Path


class BibleNavigationService:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else (
            Path(__file__).resolve().parent.parent
            / "database"
            / "bible.db"
        )

    def get_books(self, testament):
        if testament not in ("old", "new"):
            raise ValueError("Invalid testament")

        condition = (
            "(book_id BETWEEN 1 AND 39 OR book_id BETWEEN 68 AND 75)"
            if testament == "old"
            else "book_id BETWEEN 40 AND 66"
        )

        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                f"SELECT book_id, name, chapters FROM books "
                f"WHERE {condition} ORDER BY book_id"
            ).fetchall()

        return [dict(row) for row in rows]

    def get_chapters(self, book_id):
        if not isinstance(book_id, int) or isinstance(book_id, bool):
            raise ValueError("Invalid book ID")

        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT chapters FROM books WHERE book_id = ?",
                (book_id,)
            ).fetchone()

        if row is None:
            raise ValueError("Book not found")

        return list(range(1, row[0] + 1))

    def get_chapter_text(self, book_id, chapter):
        if not isinstance(book_id, int) or isinstance(book_id, bool):
            raise ValueError("Invalid book ID")

        if not isinstance(chapter, int) or isinstance(chapter, bool):
            raise ValueError("Invalid chapter")

        chapters = self.get_chapters(book_id)

        if chapter not in chapters:
            raise ValueError("Chapter out of range")

        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                """
                SELECT verse, text
                FROM verses
                WHERE book_id = ? AND chapter = ?
                ORDER BY verse
                """,
                (book_id, chapter)
            ).fetchall()

        if not rows:
            raise LookupError("Chapter text not found")

        return "\n".join(
            f"{verse}. {text}"
            for verse, text in rows
        )


    def get_book_name(self, book_id: int) -> str:
        if not isinstance(book_id, int) or isinstance(book_id, bool):
            raise ValueError("Invalid book ID")

        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT name FROM books WHERE book_id = ?",
                (book_id,),
            ).fetchone()

        if row is None:
            raise ValueError("Book not found")

        return row[0]
