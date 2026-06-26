from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import User
from bot.database.repositories.content import ContentRepository
from bot.keyboards.earn import earn_kb

router = Router()
settings = get_settings()


@router.callback_query(lambda c: c.data == "menu:earn")
async def cb_earn(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    repo = ContentRepository(session)
    template = await repo.get_text("earn")
    ref_link = f"https://t.me/{settings.bot_username}?start=ref_{db_user.user_id}"

    text = template.format(
        referrals=db_user.referrals_count,
        link=ref_link,
        balance=float(db_user.stars_balance),
    ) if "{" in template else (
        f"💸 <b>Заработать</b>\n\n"
        f"Приглашай друзей по реферальной ссылке!\n\n"
        f"👥 Приглашено: <b>{db_user.referrals_count}</b>\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )

    photo = await repo.get_photo("earn")
    kb = earn_kb(settings.bot_username, db_user.user_id)

    try:
        if photo:
            await callback.message.delete()
            await callback.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()
