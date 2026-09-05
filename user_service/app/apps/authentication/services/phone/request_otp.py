from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from app.apps.authentication.exceptions.phone import (
    PhoneAlreadyVerifiedError,
    PhoneNotVerifiedError,
)
from app.apps.authentication.exceptions.otp import OTPCooldownError

from app.apps.authentication.models import AuthMethod, VerificationToken
from app.apps.authentication.utils import token, otp
from app.apps.authentication.constants import verification_type

from app.apps.authentication.constants import phone

from app.apps.authentication.utils.cooldown import get_cool_down
from app.apps.authentication.constants import cooldown

from app.apps.notifications.services.sms_service import request_login_otp_sms


def request_phone_otp(user, login=False) -> None:
    cooldown_key = get_cool_down(cooldown.OTP_COOLDOWN, user.id)
    if cache.get(cooldown_key):
        raise OTPCooldownError("Please wait before requesting another code.")

    auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.MOBILE, is_verified=False
    ).first()

    if not auth_method and not login:
        raise PhoneAlreadyVerifiedError("This phone number is verified already!")

    if login and auth_method:
        raise PhoneNotVerifiedError(
            "This number is not verified, please choose another method to login"
        )

    if login:
        auth_method = AuthMethod.objects.filter(
            user=user, provider=AuthMethod.MOBILE, is_verified=True
        ).first()

    VerificationToken.objects.filter(
        auth_method=auth_method,
        type=verification_type.PHONE_TYPE,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())

    raw_otp = otp._generate_otp()
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PHONE_TYPE,
        token_hash=token.hash_token(raw_otp),
        expires_at=timezone.now() + timedelta(minutes=phone.OTP_TTL_MINUTES),
    )

    cache.set(cooldown_key, True, timeout=phone.OTP_RESEND_COOLDOWN_SECONDS)
    cache.delete(get_cool_down(cooldown.OTP_ATTEMPTS, user.id))
    print("user_id : ", user.id, "user phone number: ", user.phone_number)
    transaction.on_commit(
        lambda: request_login_otp_sms(str(user.id), str(user.phone_number), raw_otp)
    )
