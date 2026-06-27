import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.database.models import User
from bot.database.repositories.settings import SettingsRepository
from bot.database.repositories.user import UserRepository

logger = logging.getLogger(__name__)


async def check_referral_reward(user: User, session: AsyncSession, bot: Bot | None = None) -> None:
    """Check if this user has fulfilled conditions → pay referral reward to referrer once."""
    if user.referral_reward_given:
        logger.info("REFERRAL uid=%d: skip — reward already given", user.user_id)
        return
    if not user.referrer_id:
        logger.info("REFERRAL uid=%d: skip — no referrer_id", user.user_id)
        return

    repo = SettingsRepository(session)
    min_tasks = await repo.get_int("min_tasks_for_referral", 3)
    reward = await repo.get_float("referral_reward", 3.0)

    settings = get_settings()
    if (settings.tgrass_code or settings.botohub_key) and not user.sponsors_verified:
        logger.info("REFERRAL uid=%d: skip — sponsors_verified=False (tgrass=%r botohub=%r)",
                    user.user_id, bool(settings.tgrass_code), bool(settings.botohub_key))
        return
    if user.tasks_completed_count < min_tasks:
        logger.info("REFERRAL uid=%d: skip — tasks %d < min %d",
                    user.user_id, user.tasks_completed_count, min_tasks)
        return

    logger.info("REFERRAL uid=%d: conditions met (tasks=%d sponsors=%s referrer=%d) → giving reward %.2f",
                user.user_id, user.tasks_completed_count, user.sponsors_verified, user.referrer_id, reward)

    # All conditions met — reward the referrer
    user_repo = UserRepository(session)
    referrer = await user_repo.get(user.referrer_id)
    if not referrer:
        logger.warning("REFERRAL uid=%d: referrer %d not found", user.user_id, user.referrer_id)
        return

    user.referral_reward_given = True
    referrer.stars_balance = round(float(referrer.stars_balance) + reward, 2)
    await session.commit()

    username_display = f"@{user.username}" if user.username else user.first_name
    if bot:
        try:
            await bot.send_message(
                referrer.user_id,
                f"🎉 Вам начислено <b>{reward:.0f} ⭐</b> за пользователя {username_display}.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to notify referrer %s: %s", referrer.user_id, e)


async def notify_user_sponsors_verified(user: User, session: AsyncSession, bot: Bot) -> None:
    """Tell the referred user they've passed sponsors and how many tasks remain."""
    if not user.referrer_id or user.referral_reward_given:
        return
    repo = SettingsRepository(session)
    min_tasks = await repo.get_int("min_tasks_for_referral", 3)
    remaining = max(0, min_tasks - user.tasks_completed_count)
    if remaining <= 0:
        return
    if remaining == 1:
        word = "задание"
    elif remaining in (2, 3, 4):
        word = "задания"
    else:
        word = "заданий"
    try:
        await bot.send_message(
            user.user_id,
            f"✅ <b>Вы подписались на спонсоров!</b>\n\n"
            f"Осталось выполнить ещё <b>{remaining} {word}</b> для активации реферальной программы.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Failed to notify user %s sponsors passed: %s", user.user_id, e)


async def notify_referrer_sponsors_verified(user: User, session: AsyncSession, bot: Bot) -> None:
    """Notify referrer that their referred user passed the sponsor wall."""
    if not user.referrer_id or user.referral_reward_given:
        return
    repo = SettingsRepository(session)
    min_tasks = await repo.get_int("min_tasks_for_referral", 3)
    remaining = max(0, min_tasks - user.tasks_completed_count)
    if remaining <= 0:
        return
    username_display = f"@{user.username}" if user.username else user.first_name
    word = "задание" if remaining == 1 else "задания" if remaining in (2, 3, 4) else "заданий"
    try:
        await bot.send_message(
            user.referrer_id,
            f"✅ <b>{username_display} подписался на спонсоров!</b>\n\n"
            f"Осталось выполнить <b>{remaining} {word}</b> для получения награды.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Failed to notify referrer %s sponsors passed: %s", user.referrer_id, e)


async def notify_referrer_joined(referrer_id: int, new_user: User, session: AsyncSession, bot: Bot) -> None:
    """Notify referrer that someone joined via their link."""
    settings = get_settings()
    repo = SettingsRepository(session)
    reward = await repo.get_float("referral_reward", 3.0)
    min_tasks = await repo.get_int("min_tasks_for_referral", 3)
    username_display = f"@{new_user.username}" if new_user.username else new_user.first_name

    conditions: list[str] = []
    if settings.tgrass_code or settings.botohub_key:
        conditions.append("• подпишется на всех спонсоров;")
    conditions.append(f"• выполнит минимум <b>{min_tasks}</b> заданий.")

    try:
        await bot.send_message(
            referrer_id,
            f"⚡ Пользователь {username_display} присоединился по вашей ссылке!\n\n"
            f"Вы получите <b>{reward:.0f} ⭐</b>, когда он:\n"
            + "\n".join(conditions),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Failed to notify referrer %s of new join: %s", referrer_id, e)
