from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.user import UserRepository
from bot.config import get_settings

settings = get_settings()


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        tg_user = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        repo = UserRepository(session)
        user, is_new = await repo.get_or_create(
            user_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "",
        )

        if user.is_blocked and tg_user.id not in settings.admin_id_list:
            inner = data.get("event_context") or (
                event.message if hasattr(event, "message") else None
            ) or (event.callback_query if hasattr(event, "callback_query") else None)
            if inner and hasattr(inner, "answer"):
                await inner.answer("❌ Вы заблокированы в боте.")
            return

        if tg_user.id in settings.admin_id_list and not user.is_admin:
            user.is_admin = True
            await session.commit()

        data["db_user"] = user
        data["is_new_user"] = is_new
        return await handler(event, data)
