import asyncio
import logging

from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)


async def broadcast(bot: Bot, user_ids: list[int], source_message: Message) -> tuple[int, int]:
    """Send source_message content to all user_ids. Returns (success, fail) counts."""
    success = 0
    fail = 0
    for uid in user_ids:
        try:
            await source_message.copy_to(uid)
            success += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)  # ~20 messages/sec
    return success, fail
