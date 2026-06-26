import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
settings = get_settings()
from bot.database.engine import init_db
from bot.database.repositories.settings import SettingsRepository
from bot.database.repositories.content import ContentRepository
from bot.database.engine import SessionFactory
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.user import UserMiddleware
from bot.middlewares.sponsor_wall import SponsorWallMiddleware
from bot.handlers import router
from bot.services.lottery_scheduler import lottery_time_check_loop
from bot.services.auction_scheduler import auction_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    settings.bot_username = me.username or ""
    await init_db()
    async with SessionFactory() as session:
        settings_repo = SettingsRepository(session)
        await settings_repo.seed_defaults()
        content_repo = ContentRepository(session)
        await content_repo.seed_defaults()
    asyncio.create_task(lottery_time_check_loop(bot))
    asyncio.create_task(auction_loop(bot))
    logger.info("Database initialized. Background tasks started.")


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(UserMiddleware())
    dp.update.middleware(SponsorWallMiddleware())

    dp.include_router(router)

    dp.startup.register(on_startup)

    logger.info("Starting bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
