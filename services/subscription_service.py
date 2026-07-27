"""Сервіс керування підписками користувачів."""
from __future__ import annotations

from services.subscriptions_database import (
    SubscriptionsDatabase,
    subscriptions_db,
)


class SubscriptionService:
    def __init__(
        self,
        database: SubscriptionsDatabase | None = None,
    ) -> None:
        self.database = database or subscriptions_db

    def subscribe(
        self,
        chat_id: int,
        user_id: int | None = None,
        username: str | None = None,
        full_name: str | None = None,
    ) -> bool:
        return self.database.add(
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            full_name=full_name,
        )

    def unsubscribe(self, chat_id: int) -> bool:
        return self.database.remove(chat_id)

    def is_subscribed(self, chat_id: int) -> bool:
        return self.database.exists(chat_id)

    def get_subscriber_chat_ids(self) -> list[int]:
        return self.database.get_all_chat_ids()

    def count(self) -> int:
        return self.database.count()


subscription_service = SubscriptionService()
