"""Щоденна автоматична розсилка літургійних читань."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from config import TELEGRAM_SAFE_MESSAGE_LENGTH
from services.message_service import MessageService
from services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Europe/Kyiv"
DEFAULT_SEND_HOUR = 7
DEFAULT_SEND_MINUTE = 0


def split_telegram_text(
    text: str,
    limit: int = TELEGRAM_SAFE_MESSAGE_LENGTH,
) -> list[str]:
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


def seconds_until_next_run(
    timezone_name: str = DEFAULT_TIMEZONE,
    hour: int = DEFAULT_SEND_HOUR,
    minute: int = DEFAULT_SEND_MINUTE,
) -> float:
    timezone = ZoneInfo(timezone_name)
    now = datetime.now(timezone)

    next_run = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if next_run <= now:
        next_run += timedelta(days=1)

    return max((next_run - now).total_seconds(), 1.0)


async def send_daily_readings(
    bot: Bot,
    message_service: MessageService,
    subscription_service: SubscriptionService,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> None:
    timezone = ZoneInfo(timezone_name)
    calendar_date = datetime.now(timezone).date()
    response = message_service.build_full_text(calendar_date)

    chat_ids = subscription_service.get_subscriber_chat_ids()
    logger.info(
        "Початок щоденної розсилки на %s. Підписників: %s",
        calendar_date.isoformat(),
        len(chat_ids),
    )

    for chat_id in chat_ids:
        try:
            for message_text in response.messages:
                for chunk in split_telegram_text(message_text):
                    await bot.send_message(chat_id, chunk)
        except TelegramForbiddenError:
            logger.info(
                "Користувач %s заблокував бота. Підписку видалено.",
                chat_id,
            )
            subscription_service.unsubscribe(chat_id)
        except Exception:
            logger.exception(
                "Не вдалося надіслати читання користувачу %s",
                chat_id,
            )

    logger.info("Щоденну розсилку завершено.")


async def daily_broadcast_loop(
    bot: Bot,
    message_service: MessageService,
    subscription_service: SubscriptionService,
    timezone_name: str = DEFAULT_TIMEZONE,
    hour: int = DEFAULT_SEND_HOUR,
    minute: int = DEFAULT_SEND_MINUTE,
) -> None:
    logger.info(
        "Планувальник запущено: щодня о %02d:%02d, %s",
        hour,
        minute,
        timezone_name,
    )

    while True:
        delay = seconds_until_next_run(
            timezone_name=timezone_name,
            hour=hour,
            minute=minute,
        )
        await asyncio.sleep(delay)

        try:
            await send_daily_readings(
                bot=bot,
                message_service=message_service,
                subscription_service=subscription_service,
                timezone_name=timezone_name,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Помилка щоденної розсилки")
