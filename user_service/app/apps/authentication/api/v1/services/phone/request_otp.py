from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from app.apps.authentication.api.v1.exceptions import (
    OTPCooldownError,
    OTPInvalidError,
    OTPLockedError,
    PhoneAlreadyVerifiedError,
)
from app.apps.authentication.models import AuthMethod, VerificationToken
from app.apps.authentication.api.v1.tasks import send_otp_sms_task
from app.apps.authentication.api.v1.utils import generate_raw_token, hash_token
from app.apps.authentication.constants import verification_type

from app.apps.authentication.constants import phone


def _generate_otp() -> str:
    import secrets

    return f"{secrets.randbelow(10 ** phone.OTP_LENGTH):0{phone.OTP_LENGTH}d}"


def request_phone_otp(user) -> None:
    cooldown_key = f"otp:cooldown:{user.id}"
    if cache.get(cooldown_key):
        raise OTPCooldownError("Please wait before requesting another code.")

    auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.MOBILE, is_verified=False
    ).first()

    if not auth_method:
        raise PhoneAlreadyVerifiedError('This phone number is verified already!')

    VerificationToken.objects.filter(
        auth_method=auth_method,
        type=verification_type.PHONE_TYPE,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())

    raw_otp = _generate_otp()
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PHONE_TYPE,
        token_hash=hash_token(raw_otp),
        expires_at=timezone.now() + timedelta(minutes=phone.OTP_TTL_MINUTES),
    )

    cache.set(cooldown_key, True, timeout=phone.OTP_RESEND_COOLDOWN_SECONDS)
    cache.delete(f"otp:attempts:{user.id}")
    print("sending otp...")
    transaction.on_commit(lambda: send_otp_sms_task.delay(user.id, raw_otp))