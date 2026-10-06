from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
import logging
import requests

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def revoke_all_tokens_task(self, user_id):
    try:
        tokens = OutstandingToken.objects.filter(user_id=user_id)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def purge_notifications_task(self, user_id):
    """Delete this user's notifications when the account is deactivated.

    notification_service owns the `notifications` table in its own database, so
    there is no foreign key from here to cascade and nothing would clean up after
    a deactivated account: the rows would keep that account's notification titles,
    bodies and masked metadata indefinitely.

    A Celery task rather than a bare request in the `on_commit` hook, so a
    notification_service outage is retried instead of silently dropping the purge
    — the same reason token revocation is a task.

    Retries are bounded and then the failure is logged and dropped rather than
    raised: the account is already deactivated and must stay that way, so a purge
    that never lands is strictly better than a rollback the user cannot complete.
    Dropping it does leave rows behind, so the give-up is logged at ERROR.
    """
    url = (
        f"{settings.NOTIFICATION_SERVICE_URL}"
        f"/api/v1/notifications/internal/users/{user_id}/notifications"
    )

    try:
        response = requests.delete(
            url,
            headers={
                "X-Internal-Secret": settings.GATEWAY_INTERNAL_SECRET,
                "X-Internal-Service": "user-service",
            },
            timeout=settings.NOTIFICATION_SERVICE_TIMEOUT,
        )
        response.raise_for_status()
        logger.info("Purged notifications for user %s: %s", user_id, response.json())
    except requests.RequestException as exc:
        logger.warning(
            "Failed to purge notifications for user %s (attempt %s/%s): %s",
            user_id,
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error(
                "Giving up purging notifications for user %s after %s attempts; "
                "its notification rows may remain until they age out of retention",
                user_id,
                self.max_retries,
            )