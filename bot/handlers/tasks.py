from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import User
from bot.database.repositories.content import ContentRepository
from bot.database.repositories.settings import SettingsRepository
from bot.database.repositories.task import TaskRepository
from bot.keyboards.tasks import tasks_list_kb, task_detail_kb, pf_task_detail_kb
from bot.services.piarflow import get_sponsors, check_sponsors
from bot.services.referral import check_referral_reward

router = Router()
settings = get_settings()


def _pf_chat_id() -> int:
    try:
        if settings.admin_channel_id:
            return int(settings.admin_channel_id)
    except (ValueError, TypeError):
        pass
    return 0


async def _find_next_pf_task(s_repo: SettingsRepository, db_user: User, pf_tasks: list, skip_link: str = ""):
    """Returns (idx, sponsor) for next uncompleted PiarFlow task, or (None, None).
    skip_link: temporarily skip tasks whose link starts with this prefix (used for Skip button)."""
    for idx, sp in enumerate(pf_tasks):
        link = sp.get("link", "")
        if not link:
            continue
        if skip_link and link.startswith(skip_link[:30]):
            continue
        if await s_repo.get(f"pf_done:{db_user.user_id}:{link[:30]}", "") != "1":
            return idx, sp
    return None, None


@router.callback_query(lambda c: c.data == "menu:tasks")
async def cb_tasks_menu(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    if not settings.piarflow_key:
        s_repo = SettingsRepository(session)
        tasks_reward = await s_repo.get_float("tasks_reward", 0.3)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu:tasks"))
        builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
        try:
            await callback.message.edit_text(
                f"📋 <b>Задания</b>\n\n"
                f"Выполняй задания и получай <b>{tasks_reward:.1f} ⭐</b> за каждое!\n"
                f"✅ Выполнено: <b>{db_user.tasks_completed_count}</b>\n\n"
                "😔 Заданий пока нет. Загляни позже!",
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
        except Exception:
            pass
        await callback.answer()
        return

    await callback.answer()
    await _show_pf_task(callback, db_user, session)


async def _show_next_task(callback: CallbackQuery, db_user: User, session: AsyncSession, current_task_id: int | None = None) -> None:
    """Show next uncompleted task, or task list if none left."""
    task_repo = TaskRepository(session)
    all_tasks = await task_repo.all_active()
    completed_ids = await task_repo.completed_ids(db_user.user_id)
    uncompleted = [t for t in all_tasks if t.id not in completed_ids and t.id != current_task_id]

    if not uncompleted:
        s_repo = SettingsRepository(session)
        tasks_reward = await s_repo.get_float("tasks_reward", 0.3)
        text = (
            f"📋 <b>Задания</b>\n\n"
            f"Выполняй задания и получай <b>{tasks_reward:.1f} ⭐</b> за каждое!\n"
            f"✅ Выполнено: <b>{db_user.tasks_completed_count}</b>\n\n"
            f"🎉 Все доступные задания выполнены!"
        )
        kb = tasks_list_kb(all_tasks, completed_ids)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    task = uncompleted[0]
    text = (
        f"📌 <b>{task.title}</b>\n\n"
        f"{task.description}\n\n"
        f"💰 Награда: <b>{float(task.reward):.1f} ⭐</b>"
    )
    kb = task_detail_kb(task.id, task.url)
    if task.photo_file_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(task.photo_file_id, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("task:view:"))
async def cb_task_view(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    try:
        task_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    task_repo = TaskRepository(session)
    task = await task_repo.get(task_id)
    if not task:
        await callback.answer("Задание не найдено.", show_alert=True)
        return

    completed = await task_repo.is_completed(task_id, db_user.user_id)
    status = "✅ Выполнено" if completed else "⏳ Не выполнено"
    text = (
        f"📌 <b>{task.title}</b>\n\n"
        f"{task.description}\n\n"
        f"💰 Награда: <b>{float(task.reward):.1f} ⭐</b>\n"
        f"Статус: {status}"
    )
    kb = task_detail_kb(task_id, task.url)
    if task.photo_file_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(task.photo_file_id, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("task:check:"))
async def cb_task_check(callback: CallbackQuery, db_user: User, session: AsyncSession, bot: Bot) -> None:
    try:
        task_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    task_repo = TaskRepository(session)
    task = await task_repo.get(task_id)
    if not task:
        await callback.answer("Задание не найдено.", show_alert=True)
        return

    already = await task_repo.is_completed(task_id, db_user.user_id)
    if already:
        await callback.answer("✅ Задание уже выполнено!", show_alert=True)
        return

    if task.task_type == "channel_sub" and task.url:
        try:
            member = await bot.get_chat_member(task.url, db_user.user_id)
            if member.status in ("left", "kicked", "banned"):
                await callback.answer("❌ Вы не подписаны на канал. Подпишитесь и попробуйте ещё раз.", show_alert=True)
                return
        except Exception:
            pass

    marked = await task_repo.mark_completed(task_id, db_user.user_id)
    if marked:
        reward = float(task.reward)
        db_user.stars_balance = round(float(db_user.stars_balance) + reward, 2)
        db_user.tasks_completed_count += 1
        await session.commit()
        await callback.answer(f"✅ Задание выполнено! +{reward:.1f} ⭐", show_alert=True)
        await check_referral_reward(db_user, session, bot)
        await _show_next_task(callback, db_user, session, current_task_id=task_id)
    else:
        await callback.answer("⚠️ Не удалось отметить задание.", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("task:skip:"))
async def cb_task_skip(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    try:
        task_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer()
        return
    await callback.answer()
    await _show_next_task(callback, db_user, session, current_task_id=task_id)


@router.callback_query(lambda c: c.data == "task:already_done")
async def cb_task_already_done(callback: CallbackQuery) -> None:
    await callback.answer("✅ Это задание уже выполнено!", show_alert=True)


# ── PiarFlow task handlers (one-by-one flow) ───────────────────────────────

async def _show_pf_task(callback: CallbackQuery, db_user: User, session: AsyncSession, skip_link: str = "") -> None:
    """Shows next uncompleted PiarFlow task, or returns to tasks menu if none left."""
    s_repo = SettingsRepository(session)
    tasks_reward = await s_repo.get_float("tasks_reward", 0.3)
    max_sponsors = await s_repo.get_int("piarflow_max_sponsors", 100)
    pf_tasks = await get_sponsors(settings.piarflow_key, db_user.user_id, _pf_chat_id(), max_sponsors)

    idx, sponsor = await _find_next_pf_task(s_repo, db_user, pf_tasks, skip_link=skip_link)

    if sponsor is None:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu:tasks"))
        builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
        text = (
            f"📋 <b>Задания</b>\n\n"
            f"✅ Выполнено: <b>{db_user.tasks_completed_count}</b>\n\n"
            "🎉 Все задания выполнены! Загляни позже."
        )
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
        return

    link = sponsor.get("link", "")
    name = sponsor.get("name", "Канал")
    text = (
        f"✨ <b>Новое задание!</b> ✨\n\n"
        f"• Подпишись на канал <b>{name}</b>\n\n"
        f"Награда: <b>{tasks_reward:.1f} ⭐</b>\n\n"
        f"После выполнения жми «✅ Проверить выполнение»"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=pf_task_detail_kb(link))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=pf_task_detail_kb(link))


@router.callback_query(lambda c: c.data == "pf_task:start")
async def cb_pf_task_start(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    if not settings.piarflow_key:
        await callback.answer("Сервис недоступен.", show_alert=True)
        return
    await callback.answer()
    await _show_pf_task(callback, db_user, session)


@router.callback_query(lambda c: c.data and c.data.startswith("pf_task:skip:"))
async def cb_pf_task_skip(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    link_prefix = callback.data[len("pf_task:skip:"):]
    if not settings.piarflow_key:
        await callback.answer()
        return
    await callback.answer()
    await _show_pf_task(callback, db_user, session, skip_link=link_prefix)


@router.callback_query(lambda c: c.data and c.data.startswith("pf_task:check:"))
async def cb_pf_task_check(callback: CallbackQuery, db_user: User, session: AsyncSession, bot: Bot) -> None:
    link_prefix = callback.data[len("pf_task:check:"):]

    # Old buttons stored numeric idx — ask user to reopen the task
    if not link_prefix or link_prefix.isdigit():
        await callback.answer("Нажмите «Задания» снова для обновления.", show_alert=True)
        return

    if not settings.piarflow_key:
        await callback.answer("Сервис недоступен.", show_alert=True)
        return

    s_repo = SettingsRepository(session)
    max_sponsors = await s_repo.get_int("piarflow_max_sponsors", 100)
    tasks_reward = await s_repo.get_float("tasks_reward", 0.3)

    key = f"pf_done:{db_user.user_id}:{link_prefix[:30]}"
    if await s_repo.get(key, "") == "1":
        await callback.answer("✅ Задание уже выполнено!", show_alert=True)
        await _show_pf_task(callback, db_user, session)
        return

    pf_tasks = await get_sponsors(settings.piarflow_key, db_user.user_id, _pf_chat_id(), max_sponsors)

    # Find task by link prefix (stable across list reorderings)
    sponsor = None
    for sp in pf_tasks:
        if sp.get("link", "").startswith(link_prefix[:30]):
            sponsor = sp
            break

    if sponsor is not None:
        # Task still in PF list → user hasn't subscribed yet, verify
        full_link = sponsor.get("link", "")
        subscribed = await check_sponsors(settings.piarflow_key, db_user.user_id, [full_link])
        if not subscribed:
            await callback.answer(
                "❌ Вы не подписаны на канал. Подпишитесь и попробуйте ещё раз.",
                show_alert=True,
            )
            return
    # else: task absent from PF list → user already subscribed (PF removed it)

    await s_repo.set(key, "1")
    db_user.stars_balance = round(float(db_user.stars_balance) + tasks_reward, 2)
    db_user.tasks_completed_count += 1
    await session.commit()
    await callback.answer(f"✅ Задание выполнено! +{tasks_reward:.1f} ⭐", show_alert=True)
    await check_referral_reward(db_user, session, bot)
    await _show_pf_task(callback, db_user, session)
