from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.repositories.user import UserRepository
from bot.keyboards.admin.broadcast import broadcast_preview_kb, broadcast_cancel_kb
from bot.keyboards.admin.main import back_to_admin_kb
from bot.services.broadcast import broadcast as do_broadcast
from bot.states.admin import AdminBroadcastStates
from bot.handlers.admin.stats import _is_admin

router = Router()


@router.callback_query(lambda c: c.data == "admin:broadcast")
async def cb_broadcast(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_admin(db_user):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminBroadcastStates.waiting_message)
    try:
        await callback.message.edit_text(
            "📣 <b>Рассылка</b>\n\nОтправь сообщение (текст, фото, видео, документ или перешли сообщение):",
            parse_mode="HTML",
            reply_markup=broadcast_cancel_kb(),
        )
    except Exception:
        await callback.message.answer("📣 Отправь сообщение для рассылки:", reply_markup=broadcast_cancel_kb())
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def msg_broadcast_content(message: Message, state: FSMContext, db_user: User) -> None:
    if not _is_admin(db_user):
        return
    await state.set_state(AdminBroadcastStates.confirm)
    await state.update_data(message_id=message.message_id, chat_id=message.chat.id)

    await message.answer(
        "👆 <b>Предпросмотр выше.</b>\n\nОтправить это сообщение всем пользователям?",
        parse_mode="HTML",
        reply_markup=broadcast_preview_kb(),
    )


@router.callback_query(AdminBroadcastStates.confirm, lambda c: c.data == "admin:broadcast_confirm")
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    if not _is_admin(db_user):
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    data = await state.get_data()
    await state.clear()

    source_msg = None
    try:
        source_msg = await callback.bot.forward_message(
            chat_id=callback.message.chat.id,
            from_chat_id=data["chat_id"],
            message_id=data["message_id"],
        )
    except Exception:
        await callback.answer("⚠️ Не удалось получить сообщение.", show_alert=True)
        return

    u_repo = UserRepository(session)
    user_ids = await u_repo.all_active_ids()

    await callback.message.answer(f"⏳ Начинаю рассылку для <b>{len(user_ids)}</b> пользователей...", parse_mode="HTML")
    await callback.answer()

    success, fail = await do_broadcast(callback.bot, user_ids, source_msg)

    await callback.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"✔️ Отправлено: <b>{success}</b>\n"
        f"❌ Ошибок: <b>{fail}</b>",
        parse_mode="HTML",
        reply_markup=back_to_admin_kb(),
    )
