"""HTTP clients for the account-side data owned by user_service.

The calls go out through Kong rather than straight at the user_service
container, so the ``internal-secret-auth`` plugin verifies the shared secret on
the way in. That plugin forwards the request headers untouched, and user_service
re-verifies the secret itself, giving two independent checks on the same value.
"""

import logging

import httpx

from app.core.config import settings
from app.modules.home.exceptions import UserServiceError, UserServiceUnavailable
from app.modules.home.schemas import AccountPayload, HomeNotifications, UnreadCountPayload

logger = logging.getLogger(__name__)

ACCOUNT_PATH = "/internal/v1/users/home/{user_id}/"

# notification_service owns the in-app notifications table (it lives in its own
# database), so the unread count for the home aggregate is read from there rather
# than from user_service. The browser-facing /api/v1/notify/unread-count is not
# usable from here: Kong gates that route on a browser JWT, and this call has no
# user session. The internal variant takes the user id as a path parameter and is
# guarded by the same shared secret.
UNREAD_COUNT_PATH = "/api/v1/notifications/internal/users/{user_id}/unread-count/"


def _account_url(user_id: int) -> str:
    return f"{settings.USER_SERVICE_URL}{ACCOUNT_PATH.format(user_id=user_id)}"


def _unread_count_url(user_id: int) -> str:
    return f"{settings.NOTIFICATION_SERVICE_URL}{UNREAD_COUNT_PATH.format(user_id=user_id)}"


async def fetch_account(user_id: int) -> AccountPayload:
    """Fetch and validate the account aggregate for ``user_id``.

    Raises:
        UserServiceUnavailable: the call timed out or the host was unreachable.
        UserServiceError: any other non-2xx response, or a body that does not
            match the expected shape.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.USER_SERVICE_TIMEOUT) as client:
            response = await client.get(
                _account_url(user_id),
                headers={"X-Internal-Secret": settings.GATEWAY_INTERNAL_SECRET},
            )
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(
            "user_service unreachable for home aggregate",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise UserServiceUnavailable("Could not reach user_service") from e
    except httpx.HTTPStatusError as e:
        logger.warning(
            "user_service returned an error for home aggregate",
            extra={"user_id": user_id, "status": e.response.status_code},
        )
        raise UserServiceError(
            f"user_service returned {e.response.status_code}"
        ) from e

    try:
        return AccountPayload.model_validate(response.json())
    except ValueError as e:  # covers both json decoding and pydantic ValidationError
        logger.warning(
            "user_service returned an unparseable home payload",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise UserServiceError("user_service returned an invalid payload") from e


async def fetch_unread_count(user_id: int) -> HomeNotifications:
    """Fetch the unread notification count from notification_service.

    Raises the same errors as :func:`fetch_account`, so the router maps both
    upstream failures identically.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.NOTIFICATION_SERVICE_TIMEOUT) as client:
            response = await client.get(
                _unread_count_url(user_id),
                headers={"X-Internal-Secret": settings.GATEWAY_INTERNAL_SECRET},
            )
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(
            "notification_service unreachable for unread count",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise UserServiceUnavailable("Could not reach notification_service") from e
    except httpx.HTTPStatusError as e:
        logger.warning(
            "notification_service returned an error for unread count",
            extra={"user_id": user_id, "status": e.response.status_code},
        )
        raise UserServiceError(
            f"notification_service returned {e.response.status_code}"
        ) from e

    try:
        unread = UnreadCountPayload.model_validate(response.json())
    except ValueError as e:
        logger.warning(
            "notification_service returned an unparseable unread count",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise UserServiceError("notification_service returned an invalid payload") from e

    return HomeNotifications(unread=unread.unread)
