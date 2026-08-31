from app.config import settings
from app.apps.notifications.events.schemas import (
    AccountRegisteredPayload,
    RegistrationMethod,
    AccountVerificationPayload,
)
from app.apps.notifications.publishers.sns_publisher import publish_to_sns

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
    publish_to_sns("account.registered", user_id, payload)


def notify_account_verification(
    user_id: str, email: str, raw_token: str, email_change: bool = False
) -> bool:
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}{'&key=email_change' if email_change else ''}"
    payload = AccountVerificationPayload(
        email=email, verification_link=verification_link
    )
    return publish_to_sns("account.verification", user_id, payload)
