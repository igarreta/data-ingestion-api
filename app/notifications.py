import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


async def notify_error(message: str) -> None:
    """Send a Pushover notification for a 500-level error."""
    if not settings.pushover_user_key or not settings.pushover_api_token:
        logger.warning("Pushover credentials not configured — skipping notification")
        return

    payload = {
        "token": settings.pushover_api_token,
        "user": settings.pushover_user_key,
        "device": settings.pushover_device,
        "title": f"[{settings.hostname}] {settings.service_name} error",
        "message": message,
        "priority": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(PUSHOVER_URL, data=payload)
            response.raise_for_status()
    except Exception as exc:
        logger.error("Failed to send Pushover notification: %s", exc)
