import asyncio

from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import User
from bot.database.repositories.content import ContentRepository
from bot.database.repositories.user import UserRepository
from bot.keyboards.main import main_menu_kb
from bot.services.adv import send_ad
from bot.services.captcha import generate_fruit_captcha
from bot.services.referral import notify_referrer_joined, check_referral_reward, notify_user_sponsors_verified
from bot.states.captcha import CaptchaStates

router = Router()
settings = get_settings()


def _captcha_kb(target: str, grid: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for emoji in grid:
        builder.button(text=emoji, callback_data=f"captcha:{emoji}")
    builder.adjust(3)
    return builder.as_markup()


def _captcha_text(target: str, retry: bool = False) -> str:
    prefix = "Неверно! Попробуй ещё раз.\n\n" if retry else ""
    return f"🤖 <b>ПРОВЕРКА НА РОБОТА</b>\n\n{prefix}Нажми на кнопку, где изображено {target}"


async def _send_main_menu(message: Message, user: User, session: AsyncSession) -> None:
    repo = ContentRepository(session)
    text = await repo.get_text("welcome")
    photo = await repo.get_photo("welcome")

    if photo:
        await message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    db_user: User,
    is_new_user: bool,
    bot: Bot,
) -> None:
    args = message.text.split() if message.text else []
    ref_param = args[1] if len(args) > 1 else None

    if is_new_user and ref_param and ref_param.startswith("ref_"):
        try:
            referrer_id = int(ref_param[4:])
            if referrer_id != db_user.user_id:
                user_repo = UserRepository(session)
                referrer = await user_repo.get(referrer_id)
                if referrer and not referrer.is_blocked:
                    db_user.referrer_id = referrer_id
                    referrer.referrals_count += 1
                    await session.commit()
                    await notify_referrer_joined(referrer_id, db_user, session, bot)
        except (ValueError, IndexError):
            pass

    asyncio.create_task(send_ad(settings.botohub_views_key, db_user.user_id, hi=is_new_user))

    # Admins bypass sponsor wall
    if db_user.is_admin or db_user.user_id in settings.admin_id_list:
        db_user.sponsors_verified = True
        await session.commit()
        await _send_main_menu(message, db_user, session)
        return

    # Show sponsor wall if not verified yet
    if not db_user.sponsors_verified and (settings.tgrass_code or settings.botohub_key):
        from bot.services.tgrass import check_tgrass
        from bot.services.botohub import check_botohub
        from bot.database.repositories.settings import SettingsRepository
        import asyncio as _asyncio

        tgrass_result, botohub_result = await _asyncio.gather(
            check_tgrass(db_user.user_id, settings.tgrass_code),
            check_botohub(db_user.user_id, settings.botohub_key),
            return_exceptions=True,
        )
        botohub_list = botohub_result if isinstance(botohub_result, list) else []
        tgrass_list = tgrass_result if isinstance(tgrass_result, list) else []
        unsubscribed = botohub_list + tgrass_list

        if unsubscribed:
            s_repo = SettingsRepository(session)
            max_ch = await s_repo.get_int("sponsor_max_channels", 3)
            if max_ch > 0:
                tgrass_slots = max(0, max_ch - len(botohub_list))
                shown = (botohub_list[:max_ch] + tgrass_list[:tgrass_slots])[:max_ch]
            else:
                shown = unsubscribed

            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton
            import time as _time
            s_repo = SettingsRepository(session)
            max_ch = await s_repo.get_int("sponsor_max_channels", 10)
            total_left = len(unsubscribed)
            shown = unsubscribed[:max_ch] if max_ch > 0 else unsubscribed
            # Record timestamp for 15-min cooldown between batches
            await s_repo.set(f"sw:{db_user.user_id}", str(int(_time.time())))

            builder = InlineKeyboardBuilder()
            btns = [
                InlineKeyboardButton(text="📢 Подписаться", url=ch.get("url", ""))
                for ch in shown if ch.get("url")
            ]
            for i in range(0, len(btns), 2):
                builder.row(*btns[i:i+2])
            builder.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="sponsor_check"))

            progress = f" (ещё {total_left - len(shown)} после)" if total_left > len(shown) else ""
            await message.answer(
                f"📢 <b>Подписка на спонсоров</b>\n\n"
                f"Осталось каналов: <b>{total_left}</b>{progress}.\n\n"
                "Подпишитесь на каналы ниже и нажмите <b>«Я подписался»</b>.",
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
            return

    await _send_main_menu(message, db_user, session)


@router.callback_query(lambda c: c.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    asyncio.create_task(send_ad(settings.botohub_views_key, db_user.user_id, hi=False))
    repo = ContentRepository(session)
    text = await repo.get_text("welcome")
    photo = await repo.get_photo("welcome")

    if photo:
        try:
            await callback.message.delete()
            await callback.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
    else:
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "sponsor_check")
async def cb_sponsor_check(
    callback: CallbackQuery,
    db_user: User,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    from bot.services.tgrass import check_tgrass
    from bot.services.botohub import check_botohub

    # If no sponsor services configured — skip captcha, mark verified directly
    if not settings.tgrass_code and not settings.botohub_key:
        db_user.sponsors_verified = True
        await session.commit()
        await check_referral_reward(db_user, session, bot)
        if not db_user.referral_reward_given:
            await notify_user_sponsors_verified(db_user, session, bot)
        repo = ContentRepository(session)
        text = await repo.get_text("welcome")
        photo = await repo.get_photo("welcome")
        await callback.answer()
        if photo:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
        else:
            try:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())
            except Exception:
                await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
        return

    tgrass_result, botohub_result = await asyncio.gather(
        check_tgrass(db_user.user_id, settings.tgrass_code),
        check_botohub(db_user.user_id, settings.botohub_key),
        return_exceptions=True,
    )

    unsubscribed: list[dict] = []
    if isinstance(tgrass_result, list):
        unsubscribed.extend(tgrass_result)
    if isinstance(botohub_result, list):
        unsubscribed.extend(botohub_result)

    if unsubscribed:
        import time as _time
        from bot.database.repositories.settings import SettingsRepository
        s_repo = SettingsRepository(session)

        ts_key = f"sw:{db_user.user_id}"
        last_shown = int(float(await s_repo.get(ts_key, "0") or "0"))
        now = int(_time.time())
        cooldown = 900  # 15 минут

        if last_shown > 0 and (now - last_shown) < cooldown:
            await callback.answer(
                "❌ Вы ещё не подписались на все каналы. Попробуйте позже.",
                show_alert=True,
            )
            return

        # Show next batch and record timestamp
        await s_repo.set(ts_key, str(now))
        max_ch = await s_repo.get_int("sponsor_max_channels", 10)
        shown = unsubscribed[:max_ch] if max_ch > 0 else unsubscribed
        total_left = len(unsubscribed)

        builder = InlineKeyboardBuilder()
        btns = [
            InlineKeyboardButton(text="📢 Подписаться", url=ch.get("url", ""))
            for ch in shown if ch.get("url")
        ]
        for i in range(0, len(btns), 2):
            builder.row(*btns[i:i+2])
        builder.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="sponsor_check"))

        text = (
            "📢 <b>Подписка на спонсоров</b>\n\n"
            "Для использования бота необходимо подписаться на все каналы ниже.\n\n"
            "После подписки нажми <b>«Я подписался»</b>."
        )
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
        await callback.answer()
        return

    # All subscribed — show fruit captcha
    target, grid = generate_fruit_captcha()
    await state.set_state(CaptchaStates.waiting)
    await state.update_data(captcha_target=target)

    try:
        await callback.message.edit_text(
            _captcha_text(target),
            parse_mode="HTML",
            reply_markup=_captcha_kb(target, grid),
        )
    except Exception:
        await callback.message.answer(
            _captcha_text(target),
            parse_mode="HTML",
            reply_markup=_captcha_kb(target, grid),
        )
    await callback.answer()


@router.callback_query(CaptchaStates.waiting, lambda c: c.data and c.data.startswith("captcha:"))
async def cb_captcha_pick(
    callback: CallbackQuery,
    db_user: User,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()
    target = data.get("captcha_target", "")
    picked = callback.data[8:]  # strip "captcha:"

    if picked != target:
        new_target, new_grid = generate_fruit_captcha()
        await state.update_data(captcha_target=new_target)
        await callback.answer("❌ Неверно!", show_alert=False)
        try:
            await callback.message.edit_text(
                _captcha_text(new_target, retry=True),
                parse_mode="HTML",
                reply_markup=_captcha_kb(new_target, new_grid),
            )
        except Exception:
            pass
        return

    # Correct answer
    await state.clear()
    db_user.sponsors_verified = True
    await session.commit()
    await check_referral_reward(db_user, session, bot)
    if not db_user.referral_reward_given:
        await notify_user_sponsors_verified(db_user, session, bot)

    repo = ContentRepository(session)
    text = await repo.get_text("welcome")
    photo = await repo.get_photo("welcome")

    await callback.answer("✅ Проверка пройдена!")

    if photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
    else:
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
