from django.utils import timezone
from django.db import transaction

from app.apps.authentication.models.verification_token import VerificationToken

# constants
from app.apps.authentication.constants.verification_type import EMAIL_TYPE

# exceptions
from app.apps.authentication.exceptions.email import (
    EmailVerificationInvalidError,
)

from app.apps.authentication.utils.token import hash_token


def verify_email(*, user_id: int, raw_token: str) -> None:

    token = (
        VerificationToken.objects.select_related("auth_method", "user")
        .filter(
            user_id=user_id,
            type=EMAIL_TYPE,
            used_at__isnull=True,
            revoked_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    if token is None:
        raise EmailVerificationInvalidError(
            "Invalid or already-used verification link."
        )

    if token.expires_at < timezone.now():
        raise EmailVerificationInvalidError("This verification link has expired.")

    if token.token_hash != hash_token(raw_token):
        raise EmailVerificationInvalidError("Invalid verification link.")

    with transaction.atomic():
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])

        token.auth_method.is_verified = True
        token.auth_method.last_used_at = timezone.now()
        token.auth_method.save(update_fields=["is_verified", "last_used_at"])

        token.user.is_email_verified = True
        token.user.save(update_fields=["is_email_verified"])
