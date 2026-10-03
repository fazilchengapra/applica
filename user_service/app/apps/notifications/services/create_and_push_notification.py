import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def create_and_push(*, user, type: str, title: str, body: str, metadata: dict = None):
    """Create an in-app notification in notification_service.

    notification_service owns the `notifications` table (it lives in its own
    database, so there is nothing to read or write here). This keeps the
    historical name and signature so the per-event helpers and their
    `transaction.on_commit` call sites are unchanged.

    Realtime fan-out is notification_service's job too: it emits
    `notification.created` to the websocket group after the insert commits, so
    this function no longer touches the channel layer.

    Failures are swallowed. Every caller is an auth flow (phone verified,
    phone changed) running inside a transaction, and a notification service
    outage must not roll back a successful verification. The cost is a lost
    notification, which is recoverable; the alternative is a user who cannot
    verify their phone number.
    """
    payload = {
        "userId": user.id,
        "type": type,
        "title": title,
        "body": body,
        "metadata": metadata or {},
    }
    url = f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/internal/notifications"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "X-Internal-Secret": settings.GATEWAY_INTERNAL_SECRET,
                "X-Internal-Service": "user-service",
            },
            timeout=settings.NOTIFICATION_SERVICE_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception(
            "Failed to create notification for user %s (type=%s)", user.id, type
        )
        return None

    return response.json()
