from app.config import settings
from app.apps.notifications.events.schemas import (
    AccountRegisteredPayload,
    RegistrationMethod,
    AccountVerificationPayload,
    EmailChangedPayload,
)
from app.apps.notifications.publishers.sns_publisher import publish_to_sns

from app.apps.notifications.constants.notification_type import NotificationType


def notify_account_registered(
    user_id: str,
    email: str,
    display_name: str,
    registration_method: RegistrationMethod,
) -> None:
    payload = AccountRegisteredPayload(
        email=email,
        display_name=display_name,
        registration_method=registration_method,
    )
    publish_to_sns(NotificationType.REGISTERED, user_id, payload)


def notify_account_verification(
    user_id: str, email: str, raw_token: str, email_change: bool = False
) -> bool:
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}{'&key=email_change' if email_change else ''}"
    payload = AccountVerificationPayload(
        email=email, verification_link=verification_link
    )
    return publish_to_sns(
        (
            NotificationType.ACCOUNT_VERIFICATION_REQ
            if not email_change
            else NotificationType.EMAIL_CHANGE_REQ
        ),
        user_id,
        payload,
    )


def notify_email_changed(email: str, old_email: str, user_id: str) -> bool:
    payload = EmailChangedPayload(email=email, old_email=old_email)
    return publish_to_sns(NotificationType.EMAIL_CHANGED, user_id, payload)
