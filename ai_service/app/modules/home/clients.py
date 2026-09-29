"""HTTP client for the account-side data owned by user_service.

The call goes out through Kong rather than straight at the user_service
container, so the ``internal-secret-auth`` plugin verifies the shared secret on
the way in. That plugin forwards the request headers untouched, and user_service
re-verifies the secret itself, giving two independent checks on the same value.
"""

import logging

import httpx

from app.core.config import settings
from app.modules.home.exceptions import UserServiceError, UserServiceUnavailable
from app.modules.home.schemas import AccountPayload

logger = logging.getLogger(__name__)

ACCOUNT_PATH = "/internal/v1/users/home/{user_id}/"


def _account_url(user_id: int) -> str:
    return f"{settings.USER_SERVICE_URL}{ACCOUNT_PATH.format(user_id=user_id)}"


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
