import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import User

settings = get_settings()
logger = logging.getLogger(__name__)

_BYPASS_PREFIXES = (
    "/start", "/admin",
    "admin:", "wall_check", "sponsor_check", "captcha:",
)


def _should_skip(cb_data: str | None, msg_text: str | None) -> bool:
    if msg_text and any(msg_text.startswith(p) for p in _BYPASS_PREFIXES):
        return True
    if cb_data and any(cb_data.startswith(p) for p in _BYPASS_PREFIXES):
        return True
    return False


class SponsorWallMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        if not db_user:
            return await handler(event, data)

        if db_user.is_admin or db_user.user_id in settings.admin_id_list:
            return await handler(event, data)

        inner: Message | CallbackQuery | None = None
        if isinstance(event, Update):
            inner = event.message or event.callback_query
        elif isinstance(event, (Message, CallbackQuery)):
            inner = event

        cb_data = inner.data if isinstance(inner, CallbackQuery) else None
        msg_text = inner.text if isinstance(inner, Message) else None

        if _should_skip(cb_data, msg_text):
            return await handler(event, data)

        if db_user.sponsors_verified:
            return await handler(event, data)

        uid = db_user.user_id
        logger.info("WALL uid=%s tgrass=%r botohub=%r", uid, bool(settings.tgrass_code), bool(settings.botohub_key))

        # No sponsor services configured — auto-verify
        if not settings.tgrass_code and not settings.botohub_key:
            logger.info("WALL uid=%s auto-verify (no services)", uid)
            db_user.sponsors_verified = True
            session: AsyncSession = data.get("session")
            if session:
                await session.commit()
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        from bot.services.tgrass import check_tgrass
        from bot.services.botohub import check_botohub
        from bot.database.repositories.settings import SettingsRepository

        tgrass_result, botohub_result = await asyncio.gather(
            check_tgrass(db_user.user_id, settings.tgrass_code),
            check_botohub(db_user.user_id, settings.botohub_key),
            return_exceptions=True,
        )

        logger.info("WALL uid=%s tgrass_result=%s botohub_result=%s", uid, type(tgrass_result).__name__, type(botohub_result).__name__)
        if isinstance(tgrass_result, list):
            logger.info("WALL uid=%s tgrass_count=%d", uid, len(tgrass_result))
        else:
            logger.warning("WALL uid=%s tgrass_error=%s", uid, tgrass_result)
        if isinstance(botohub_result, list):
            logger.info("WALL uid=%s botohub_count=%d", uid, len(botohub_result))
        else:
            logger.warning("WALL uid=%s botohub_error=%s", uid, botohub_result)

        botohub_list = botohub_result if isinstance(botohub_result, list) else []
        tgrass_list = tgrass_result if isinstance(tgrass_result, list) else []
        unsubscribed = botohub_list + tgrass_list

        logger.info("WALL uid=%s total_unsubscribed=%d (botohub=%d tgrass=%d)",
                    uid, len(unsubscribed), len(botohub_list), len(tgrass_list))

        if not unsubscribed:
            logger.info("WALL uid=%s all-subscribed → verify", uid)
            db_user.sponsors_verified = True
            await session.commit()
            from bot.services.referral import check_referral_reward, notify_user_sponsors_verified
            await check_referral_reward(db_user, session, data.get("bot"))
            if not db_user.referral_reward_given:
                bot = data.get("bot")
                if bot:
                    await notify_user_sponsors_verified(db_user, session, bot)
            return await handler(event, data)

        # Show ALL unsubscribed channels at once so user can subscribe in one go
        builder = InlineKeyboardBuilder()
        btns = [
            InlineKeyboardButton(text="📢 Подписаться", url=ch.get("url", ""))
            for ch in unsubscribed if ch.get("url")
        ]
        for i in range(0, len(btns), 2):
            builder.row(*btns[i:i+2])
        builder.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="sponsor_check"))

        total_left = len(unsubscribed)
        text = (
            f"📢 <b>Подписка на спонсоров</b>\n\n"
            f"Осталось подписаться: <b>{total_left} канала(-ов)</b>.\n\n"
            "Подпишитесь на все каналы ниже и нажмите <b>«Я подписался»</b>."
        )

        if isinstance(inner, Message):
            await inner.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
        elif isinstance(inner, CallbackQuery):
            try:
                await inner.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
            except Exception:
                await inner.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
            await inner.answer()
        return
