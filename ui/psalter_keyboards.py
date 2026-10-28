"""Inline keyboards for the Psalter."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PSALM_COUNT = 150
PAGE_SIZE = 10


def psalter_list_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    total_pages = (PSALM_COUNT + PAGE_SIZE - 1) // PAGE_SIZE

    if not 0 <= page < total_pages:
        raise ValueError("Invalid Psalter page")

    start = page * PAGE_SIZE + 1
    end = min(start + PAGE_SIZE - 1, PSALM_COUNT)

    rows = []

    for number in range(start, end + 1, 2):
        row = [
            InlineKeyboardButton(
                text=str(psalm),
                callback_data=f"psalter_open:{psalm}",
            )
            for psalm in range(number, min(number + 1, end) + 1)
        ]
        rows.append(row)

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="\u2b05\ufe0f",
                callback_data=f"psalter_list:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                text="\u27a1\ufe0f",
                callback_data=f"psalter_list:{page + 1}",
            )
        )

    if navigation:
        rows.append(navigation)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def psalter_navigation_keyboard(psalm: int) -> InlineKeyboardMarkup:
    if not 1 <= psalm <= PSALM_COUNT:
        raise ValueError("Invalid psalm number")

    rows = []
    navigation = []

    if psalm > 1:
        navigation.append(
            InlineKeyboardButton(
                text="\u2b05\ufe0f",
                callback_data=f"psalter_open:{psalm - 1}",
            )
        )

    if psalm < PSALM_COUNT:
        navigation.append(
            InlineKeyboardButton(
                text="\u27a1\ufe0f",
                callback_data=f"psalter_open:{psalm + 1}",
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append([
        InlineKeyboardButton(
            text="\U0001f4d6 \u0421\u043f\u0438\u0441\u043e\u043a \u043f\u0441\u0430\u043b\u043c\u0456\u0432",
            callback_data=f"psalter_list:{(psalm - 1) // PAGE_SIZE}",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
