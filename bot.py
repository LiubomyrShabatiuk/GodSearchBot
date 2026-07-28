"""Telegram-бот щоденних літургійних читань."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from config import BOT_TOKEN, TELEGRAM_SAFE_MESSAGE_LENGTH
from services.bible_service import BibleService
from services.favorites_service import FavoritesService
from services.message_service import MessageService
from services.readings_service import ReadingsService
from services.scheduler_service import daily_broadcast_loop
from services.subscription_service import SubscriptionService
from ui.keyboards import (
    MAIN_KEYBOARD,
    favorites_list_keyboard,
    navigation_keyboard,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

readings_service = ReadingsService()
bible_service = BibleService()
subscription_service = SubscriptionService()
favorites_service = FavoritesService()

message_service = MessageService(
    readings_service=readings_service,
    bible_service=bible_service,
)

DATE_PATTERN = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})$"
)


def split_telegram_text(
    text: str,
    limit: int = TELEGRAM_SAFE_MESSAGE_LENGTH,
) -> list[str]:
    """Розділяє довгий текст на безпечні Telegram-повідомлення."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit

        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()

    return chunks


async def send_long_message(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chunks = split_telegram_text(text)

    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)


async def send_references(
    message: Message,
    value: str | date | None,
) -> None:
    try:
        response = message_service.build_references(value)
        user = message.from_user
        is_favorite = (
            favorites_service.exists(user.id, response.calendar_date)
            if user
            else False
        )
        await message.answer(
            response.messages[0],
            reply_markup=navigation_keyboard(
                response.calendar_date,
                is_favorite=is_favorite,
            ),
        )
    except (ValueError, TypeError):
        await message.answer(
            "Неправильний формат дати. Використовуйте "
            "31.10.2026 або 2026-10-31."
        )


async def send_full_readings(
    message: Message,
    value: str | date | None,
) -> None:
    await message.answer("⏳ Готую повний текст читань…")

    try:
        response = message_service.build_full_text(value)
    except (ValueError, TypeError):
        await message.answer(
            "Неправильний формат дати. Приклад: 31.10.2026"
        )
        return
    except Exception as error:
        logger.exception("Помилка повного тексту")
        await message.answer(
            "Не вдалося отримати повний текст.\n"
            f"Технічна причина: {type(error).__name__}: {error}"
        )
        return

    for index, text in enumerate(response.messages):
        user = message.from_user
        is_favorite = (
            favorites_service.exists(user.id, response.calendar_date)
            if user
            else False
        )
        markup = (
            navigation_keyboard(
                response.calendar_date,
                is_favorite=is_favorite,
            )
            if index == len(response.messages) - 1
            else None
        )
        await send_long_message(message, text, reply_markup=markup)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Слава Ісусу Христу!\n\n"
        "Я допоможу знайти літургійні читання "
        "Мукачівської греко-католицької єпархії.\n\n"
        "Користуйтеся кнопками нижче. Також можна надіслати "
        "дату у форматі 31.10.2026.",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command("subscribe"))
@router.message(F.text == "🔔 Підписатися")
async def subscribe_handler(message: Message) -> None:
    user = message.from_user

    created = subscription_service.subscribe(
        chat_id=message.chat.id,
        user_id=user.id if user else None,
        username=user.username if user else None,
        full_name=user.full_name if user else None,
    )

    if created:
        await message.answer(
            "🔔 Підписку активовано.\n\n"
            "Щодня о 07:00 ви автоматично отримуватимете "
            "повний текст літургійних читань.",
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await message.answer(
            "🔔 Ви вже підписані на щоденні читання.",
            reply_markup=MAIN_KEYBOARD,
        )


@router.message(Command("unsubscribe"))
@router.message(F.text == "🔕 Відписатися")
async def unsubscribe_handler(message: Message) -> None:
    removed = subscription_service.unsubscribe(message.chat.id)

    if removed:
        await message.answer(
            "🔕 Підписку скасовано. Щоденна розсилка більше "
            "не надходитиме.",
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await message.answer(
            "У вас немає активної підписки.",
            reply_markup=MAIN_KEYBOARD,
        )


@router.message(Command("favorites"))
@router.message(F.text == "⭐ Моє обране")
async def favorites_handler(message: Message) -> None:
    user = message.from_user

    if not user:
        await message.answer(
            "Не вдалося визначити користувача.",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    favorites = favorites_service.get_all(user.id)

    if not favorites:
        await message.answer(
            "⭐ У вашому обраному поки немає читань.\n\n"
            "Відкрийте потрібну дату й натисніть «⭐ Зберегти».",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    await message.answer(
        f"⭐ Моє обране\n\nЗбережено читань: {len(favorites)}\n"
        "Оберіть дату:",
        reply_markup=favorites_list_keyboard(
            [item.reading_date for item in favorites]
        ),
    )


@router.message(Command("today"))
@router.message(F.text == "📖 Сьогодні")
async def today_handler(message: Message) -> None:
    await send_references(message, date.today())


@router.message(F.text == "⬅️ Вчора")
async def yesterday_handler(message: Message) -> None:
    await send_references(message, date.today() - timedelta(days=1))


@router.message(F.text == "➡️ Завтра")
async def tomorrow_handler(message: Message) -> None:
    await send_references(message, date.today() + timedelta(days=1))


@router.message(Command("full"))
async def full_command_handler(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    value = parts[1] if len(parts) > 1 else None
    await send_full_readings(message, value)


@router.message(F.text == "📚 Повний текст на сьогодні")
async def full_today_handler(message: Message) -> None:
    await send_full_readings(message, date.today())


@router.message(Command("date"))
async def date_command_handler(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Після команди вкажіть дату.\n"
            "Наприклад: /date 2026-10-31"
        )
        return

    await send_references(message, parts[1])


@router.message(F.text == "📅 Вибрати дату")
async def choose_date_handler(message: Message) -> None:
    await message.answer(
        "Надішліть потрібну дату у форматі:\n"
        "31.10.2026 або 2026-10-31.\n\n"
        "Після цього з'явиться кнопка «📚 Повний текст»."
    )


@router.message(F.text.regexp(DATE_PATTERN))
async def plain_date_handler(message: Message) -> None:
    await send_references(message, message.text or "")


@router.callback_query(F.data.startswith("refs:"))
async def references_callback(callback: CallbackQuery) -> None:
    value = (callback.data or "").split(":", maxsplit=1)[1]

    try:
        response = message_service.build_references(value)

        if callback.message:
            await callback.message.edit_text(
                response.messages[0],
                reply_markup=navigation_keyboard(
                    response.calendar_date,
                    is_favorite=favorites_service.exists(
                        callback.from_user.id,
                        response.calendar_date,
                    ),
                ),
            )

        await callback.answer()
    except (ValueError, TypeError):
        await callback.answer("Неправильна дата.", show_alert=True)
    except Exception:
        logger.exception("Помилка навігації за датами")
        await callback.answer(
            "Не вдалося відкрити читання.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("favorite_add:"))
async def favorite_add_callback(callback: CallbackQuery) -> None:
    value = (callback.data or "").split(":", maxsplit=1)[1]

    try:
        calendar_date = favorites_service.normalize_date(value)

        if not readings_service.has_readings(calendar_date):
            await callback.answer(
                "На цю дату читання не знайдено.",
                show_alert=True,
            )
            return

        created = favorites_service.add(
            callback.from_user.id,
            calendar_date,
        )

        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=navigation_keyboard(
                    calendar_date,
                    is_favorite=True,
                )
            )

        await callback.answer(
            "⭐ Читання збережено в обране."
            if created
            else "Це читання вже є в обраному."
        )
    except (ValueError, TypeError):
        await callback.answer("Неправильна дата.", show_alert=True)
    except Exception:
        logger.exception("Помилка додавання в обране")
        await callback.answer(
            "Не вдалося зберегти читання.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("favorite_delete:"))
async def favorite_delete_callback(callback: CallbackQuery) -> None:
    value = (callback.data or "").split(":", maxsplit=1)[1]

    try:
        calendar_date = favorites_service.normalize_date(value)
        removed = favorites_service.remove(
            callback.from_user.id,
            calendar_date,
        )

        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=navigation_keyboard(
                    calendar_date,
                    is_favorite=False,
                )
            )

        await callback.answer(
            "🗑 Читання видалено з обраного."
            if removed
            else "Цього читання вже немає в обраному."
        )
    except (ValueError, TypeError):
        await callback.answer("Неправильна дата.", show_alert=True)
    except Exception:
        logger.exception("Помилка видалення з обраного")
        await callback.answer(
            "Не вдалося видалити читання.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("favorite_open:"))
async def favorite_open_callback(callback: CallbackQuery) -> None:
    value = (callback.data or "").split(":", maxsplit=1)[1]

    try:
        response = message_service.build_references(value)

        if not favorites_service.exists(
            callback.from_user.id,
            response.calendar_date,
        ):
            await callback.answer(
                "Цього читання вже немає в обраному.",
                show_alert=True,
            )
            return

        if callback.message:
            await callback.message.edit_text(
                response.messages[0],
                reply_markup=navigation_keyboard(
                    response.calendar_date,
                    is_favorite=True,
                ),
            )

        await callback.answer()
    except (ValueError, TypeError):
        await callback.answer("Неправильна дата.", show_alert=True)
    except Exception:
        logger.exception("Помилка відкриття обраного")
        await callback.answer(
            "Не вдалося відкрити читання.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("full:"))
async def full_callback(callback: CallbackQuery) -> None:
    value = (callback.data or "").split(":", maxsplit=1)[1]
    await callback.answer()

    if callback.message:
        await send_full_readings(callback.message, value)


@router.message()
async def fallback_handler(message: Message) -> None:
    await message.answer(
        "Я не розпізнав повідомлення. Натисніть кнопку "
        "або введіть дату, наприклад 31.10.2026.",
        reply_markup=MAIN_KEYBOARD,
    )


async def run_bot() -> None:
    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    scheduler_task = asyncio.create_task(
        daily_broadcast_loop(
            bot=bot,
            message_service=message_service,
            subscription_service=subscription_service,
        )
    )

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_bot())
