from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from app.apps.authentication.api.v1.exceptions import (
    OTPInvalidError,
    OTPLockedError,
)
from app.apps.authentication.models import VerificationToken
from app.apps.authentication.api.v1.tasks import send_otp_sms_task
from app.apps.authentication.utils import otp, token as tokens

from app.apps.authentication.constants import phone, verification_type

def verify_phone_otp(user, code: str) -> None:
    attempts_key = f"otp:attempts:{user.id}"
    attempts = cache.get(attempts_key, 0)
    if attempts >= phone.OTP_MAX_ATTEMPTS:
        raise OTPLockedError("Too many incorrect attempts. Request a new code.")

    token = (
        VerificationToken.objects.select_related("auth_method")
        .filter(
            user=user,
            type=verification_type.PHONE_TYPE,
            used_at__isnull=True,
            revoked_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    if token is None or token.expires_at < timezone.now():
        raise OTPInvalidError("Code expired or not found. Request a new one.")

    if token.token_hash != tokens.hash_token(code):
        cache.set(attempts_key, attempts + 1, timeout=phone.OTP_TTL_MINUTES * 60)
        raise OTPInvalidError("Incorrect code.")

    with transaction.atomic():
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])

        token.auth_method.is_verified = True
        token.auth_method.last_used_at = timezone.now()
        token.auth_method.save(update_fields=["is_verified", "last_used_at"])

        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])

    cache.delete(attempts_key)
    cache.delete(f"otp:cooldown:{user.id}")