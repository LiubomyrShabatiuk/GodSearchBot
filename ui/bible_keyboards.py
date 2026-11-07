"""Inline keyboards for Bible navigation."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def bible_testament_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u25b6\ufe0f \u041f\u0440\u043e\u0434\u043e\u0432\u0436\u0438\u0442\u0438 \u0447\u0438\u0442\u0430\u043d\u043d\u044f",
                    callback_data="bible_continue",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4dc \u0421\u0442\u0430\u0440\u0438\u0439 \u0417\u0430\u0432\u0456\u0442",
                    callback_data="bible_testament:old",
                ),
                InlineKeyboardButton(
                    text="\u271d\ufe0f \u041d\u043e\u0432\u0438\u0439 \u0417\u0430\u0432\u0456\u0442",
                    callback_data="bible_testament:new",
                ),
            ],
        ]
    )


BOOKS_PAGE_SIZE = 10


def bible_books_keyboard(
    books: list[dict],
    testament: str,
    page: int = 0,
) -> InlineKeyboardMarkup:
    if testament not in ("old", "new"):
        raise ValueError("Invalid testament")

    total_pages = max(
        1, (len(books) + BOOKS_PAGE_SIZE - 1) // BOOKS_PAGE_SIZE
    )

    if not 0 <= page < total_pages:
        raise ValueError("Invalid page")

    start = page * BOOKS_PAGE_SIZE
    end = start + BOOKS_PAGE_SIZE

    rows = []

    for book in books[start:end]:
        rows.append([
            InlineKeyboardButton(
                text=book["name"],
                callback_data=f'bible_book:{book["book_id"]}',
            )
        ])

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="\u2b05\ufe0f",
                callback_data=f"bible_books:{testament}:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                text="\u27a1\ufe0f",
                callback_data=f"bible_books:{testament}:{page + 1}",
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append([
        InlineKeyboardButton(
            text="\u2b05\ufe0f \u0414\u043e \u0432\u0438\u0431\u043e\u0440\u0443 \u0417\u0430\u0432\u0456\u0442\u0443",
            callback_data="bible_home",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

BOOKS_PAGE_SIZE = 10



CHAPTERS_PAGE_SIZE = 25


def bible_chapters_keyboard(
    book_id: int,
    chapters: list[int],
    page: int = 0,
) -> InlineKeyboardMarkup:
    total_pages = max(
        1, (len(chapters) + CHAPTERS_PAGE_SIZE - 1)
        // CHAPTERS_PAGE_SIZE
    )

    if not 0 <= page < total_pages:
        raise ValueError("Invalid page")

    start = page * CHAPTERS_PAGE_SIZE
    visible = chapters[start:start + CHAPTERS_PAGE_SIZE]

    rows = []

    for i in range(0, len(visible), 5):
        rows.append([
            InlineKeyboardButton(
                text=str(chapter),
                callback_data=f"bible_chapter:{book_id}:{chapter}",
            )
            for chapter in visible[i:i + 5]
        ])

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="\u2b05\ufe0f",
                callback_data=f"bible_chapters:{book_id}:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                text="\u27a1\ufe0f",
                callback_data=f"bible_chapters:{book_id}:{page + 1}",
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append([
        InlineKeyboardButton(
            text="\u2b05\ufe0f \u0414\u043e \u0441\u043f\u0438\u0441\u043a\u0443 \u043a\u043d\u0438\u0433",
            callback_data=f"bible_back_books:{book_id}",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def bible_chapter_navigation_keyboard(
    book_id: int,
    chapter: int,
    total_chapters: int,
) -> InlineKeyboardMarkup:
    if not 1 <= chapter <= total_chapters:
        raise ValueError("Invalid chapter")

    navigation = []

    if chapter > 1:
        navigation.append(
            InlineKeyboardButton(
                text=f"\u2b05\ufe0f {chapter - 1}",
                callback_data=f"bible_chapter:{book_id}:{chapter - 1}",
            )
        )

    if chapter < total_chapters:
        navigation.append(
            InlineKeyboardButton(
                text=f"{chapter + 1} \u27a1\ufe0f",
                callback_data=f"bible_chapter:{book_id}:{chapter + 1}",
            )
        )

    rows = []

    if navigation:
        rows.append(navigation)

    rows.append([
        InlineKeyboardButton(
            text="\U0001f4da \u0414\u043e \u0441\u043f\u0438\u0441\u043a\u0443 \u0440\u043e\u0437\u0434\u0456\u043b\u0456\u0432",
            callback_data=f"bible_chapters:{book_id}:{(chapter - 1) // 25}",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
