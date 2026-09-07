import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def publish_event(event_type: str, user_id: str, payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/realtime/cv-status",
                json={
                    "userId": str(user_id),
                    "cvId": str(payload["cv_id"]),
                    "status": payload["status"],
                },
            )
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception(
            "Failed to publish CV status",
            extra={"event_type": event_type, "user_id": str(user_id)},
        )
