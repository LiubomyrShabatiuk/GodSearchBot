"""Клавіатури Telegram."""
from datetime import date, timedelta

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="⬅️ Вчора"),
            KeyboardButton(text="📖 Сьогодні"),
            KeyboardButton(text="➡️ Завтра"),
        ],
        [KeyboardButton(text="📚 Повний текст на сьогодні")],
        [KeyboardButton(text="🔎 Пошук по Біблії")],
        [
            KeyboardButton(text="📅 Вибрати дату"),
            KeyboardButton(text="⭐ Моє обране"),
        ],
        [
            KeyboardButton(text="🔔 Підписатися"),
            KeyboardButton(text="🔕 Відписатися"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Оберіть дію або введіть дату",
)


def navigation_keyboard(
    calendar_date: date,
    is_favorite: bool = False,
) -> InlineKeyboardMarkup:
    """Створює навігацію та керування обраним для дати."""
    previous_date = calendar_date - timedelta(days=1)
    next_date = calendar_date + timedelta(days=1)
    iso_date = calendar_date.isoformat()

    favorite_button = InlineKeyboardButton(
        text=(
            "🗑 Видалити з обраного"
            if is_favorite
            else "⭐ Зберегти"
        ),
        callback_data=(
            f"favorite_delete:{iso_date}"
            if is_favorite
            else f"favorite_add:{iso_date}"
        ),
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Попередній день",
                    callback_data=f"refs:{previous_date.isoformat()}",
                ),
                InlineKeyboardButton(
                    text="➡️ Наступний день",
                    callback_data=f"refs:{next_date.isoformat()}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📚 Повний текст",
                    callback_data=f"full:{iso_date}",
                )
            ],
            [favorite_button],
            [
                InlineKeyboardButton(
                    text="📅 Сьогодні",
                    callback_data=f"refs:{date.today().isoformat()}",
                )
            ],
        ]
    )


def favorites_list_keyboard(
    favorite_dates: list[date],
) -> InlineKeyboardMarkup:
    """Створює список кнопок із датами, збереженими в обраному."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"📖 {calendar_date.strftime('%d.%m.%Y')}",
                callback_data=(
                    f"favorite_open:{calendar_date.isoformat()}"
                ),
            )
        ]
        for calendar_date in favorite_dates
    ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_pagination_keyboard(
    token: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup | None:
    """Створює навігацію між сторінками результатів пошуку."""
    buttons: list[InlineKeyboardButton] = []

    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Попередня",
                callback_data=f"search_page:{token}:{page - 1}",
            )
        )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="➡️ Наступна",
                callback_data=f"search_page:{token}:{page + 1}",
            )
        )

    if not buttons:
        return None

    return InlineKeyboardMarkup(inline_keyboard=[buttons])
