import logging

import aiohttp

logger = logging.getLogger(__name__)

_ADV_URL = "https://views.botohub.me/ad/SendPost"


async def send_ad(api_key: str, user_id: int, hi: bool = False) -> None:
    """Fire-and-forget ad delivery. hi=True only after /start for new users."""
    if not api_key:
        return
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as client:
            async with client.post(
                _ADV_URL,
                json={"SendToChatId": user_id, "hi": hi},
                headers={"Authorization": api_key, "Content-Type": "application/json"},
            ) as resp:
                data = await resp.json(content_type=None)
                code = data.get("SendPostResult", 0)
                if code not in (1, 7, 8):
                    logger.debug("Ad result for user %s: code=%s", user_id, code)
    except Exception as e:
        logger.debug("Ad send error for user %s: %s", user_id, e)
