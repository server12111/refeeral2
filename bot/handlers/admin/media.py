from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.repositories.content import ContentRepository, CONTENT_KEYS
from bot.keyboards.admin.media import media_list_kb, media_edit_kb as media_item_kb, media_cancel_kb
from bot.keyboards.admin.main import back_to_admin_kb
from bot.states.admin import AdminMediaStates
from bot.handlers.admin.stats import _is_admin

router = Router()


@router.callback_query(lambda c: c.data == "admin:media")
async def cb_media(callback: CallbackQuery, db_user: User) -> None:
    if not _is_admin(db_user): return
    text = "🖼 <b>Медиа и тексты</b>\n\nВыбери раздел для редактирования:"
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=media_list_kb())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=media_list_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data and (c.data.startswith("admin:media_edit:") or c.data.startswith("admin:media_view:")))
async def cb_media_view(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    if not _is_admin(db_user): return
    key = callback.data.rsplit(":", 1)[-1]
    if key not in CONTENT_KEYS:
        await callback.answer("❓ Неизвестный ключ.", show_alert=True)
        return
    repo = ContentRepository(session)
    item = await repo.get(key)
    text_val = (item.text if item else None) or "(не задан)"
    has_photo = bool(item and item.photo_file_id) if item else False
    msg = (
        f"📝 <b>{CONTENT_KEYS[key]}</b>\n\n"
        f"Текст:\n<code>{text_val[:1000]}</code>\n\n"
        f"Фото: {'✅ есть' if has_photo else '❌ нет'}"
    )
    try:
        await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=media_item_kb(key))
    except Exception:
        await callback.message.answer(msg, parse_mode="HTML", reply_markup=media_item_kb(key))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("admin:media_text:"))
async def cb_media_text(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_admin(db_user): return
    key = callback.data.rsplit(":", 1)[-1]
    await state.set_state(AdminMediaStates.enter_text)
    await state.update_data(content_key=key)
    await callback.message.answer(
        f"✏️ Отправь новый текст для <b>{CONTENT_KEYS.get(key, key)}</b>.\n\nМожно использовать HTML-разметку.",
        parse_mode="HTML",
        reply_markup=media_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminMediaStates.enter_text)
async def msg_media_text(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    if not _is_admin(db_user): return
    data = await state.get_data()
    key = data["content_key"]
    await state.clear()
    repo = ContentRepository(session)
    await repo.set_text(key, message.html_text or message.caption_html or message.text or message.caption or "")
    await message.answer(f"✅ Текст для <b>{CONTENT_KEYS.get(key, key)}</b> обновлён.", parse_mode="HTML", reply_markup=back_to_admin_kb())


@router.callback_query(lambda c: c.data and c.data.startswith("admin:media_photo:"))
async def cb_media_photo(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_admin(db_user): return
    key = callback.data.rsplit(":", 1)[-1]
    await state.set_state(AdminMediaStates.enter_photo)
    await state.update_data(content_key=key)
    await callback.message.answer(
        f"🖼 Отправь фото для <b>{CONTENT_KEYS.get(key, key)}</b>.\n\nИли '-' чтобы удалить текущее.",
        parse_mode="HTML",
        reply_markup=media_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminMediaStates.enter_photo)
async def msg_media_photo(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    if not _is_admin(db_user): return
    data = await state.get_data()
    key = data["content_key"]
    await state.clear()
    repo = ContentRepository(session)

    if message.text and message.text.strip() == "-":
        await repo.set_photo(key, None)
        await message.answer(f"✅ Фото для <b>{CONTENT_KEYS.get(key, key)}</b> удалено.", parse_mode="HTML", reply_markup=back_to_admin_kb())
        return

    if not message.photo:
        await message.answer("❌ Отправь фото или '-' для удаления.", reply_markup=media_cancel_kb())
        return

    file_id = message.photo[-1].file_id
    await repo.set_photo(key, file_id)
    await message.answer(f"✅ Фото для <b>{CONTENT_KEYS.get(key, key)}</b> обновлено.", parse_mode="HTML", reply_markup=back_to_admin_kb())


