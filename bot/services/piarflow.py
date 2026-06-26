import logging
import aiohttp

logger = logging.getLogger(__name__)

PIARFLOW_API = "https://piarflow.com/v1"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def get_sponsors(api_key: str, user_id: int, chat_id: int, max_sponsors: int = 3) -> list[dict]:
    """Get list of sponsor channels for user. Returns [{link, status, price}, ...]"""
    if not api_key:
        return []
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client:
            async with client.post(
                f"{PIARFLOW_API}/sponsors",
                json={"user_id": user_id, "chat_id": chat_id, "max_sponsors": max_sponsors},
                headers=_headers(api_key),
            ) as resp:
                data = await resp.json(content_type=None)
                return data.get("sponsors", [])
    except Exception as e:
        logger.warning("PiarFlow get_sponsors error: %s", e)
    return []


async def check_sponsors(api_key: str, user_id: int, links: list[str]) -> bool:
    """Check if user subscribed to all given links. Returns True if all subscribed."""
    if not api_key or not links:
        return True
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as client:
            async with client.post(
                f"{PIARFLOW_API}/sponsors/check",
                json={"user_id": user_id, "links": links},
                headers=_headers(api_key),
            ) as resp:
                data = await resp.json(content_type=None)
                sponsors = data.get("sponsors", [])
                if not sponsors:
                    return False
                return all(s.get("status") == "subscribed" for s in sponsors)
    except Exception as e:
        logger.warning("PiarFlow check_sponsors error: %s", e)
    return False
