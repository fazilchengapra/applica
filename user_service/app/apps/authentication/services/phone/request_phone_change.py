from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from ...exceptions import (
    OTPCooldownError,
    PhoneNumberInUseError,
    PhoneChangeInvalidError,
    PhoneNotVerifiedError,
    SamePhoneNumberError,
)
from app.apps.authentication.tasks import send_otp_sms_task
from app.apps.authentication.constants import phone, verification_type
from app.apps.authentication.models import AuthMethod, VerificationToken
from app.apps.authentication.utils import otp, token

from app.apps.authentication.utils.cooldown import get_cool_down
from app.apps.authentication.constants import cooldown

User = get_user_model()

PHONE_CHANGE_TTL_MINUTES = phone.OTP_TTL_MINUTES


def request_phone_change(user, new_phone_number: str) -> None:
    if User.objects.filter(phone_number=new_phone_number).exclude(id=user.id).exists():
        raise PhoneNumberInUseError("This phone number is already in use.")

    cooldown_key = get_cool_down(cooldown.PHONE_CHANGE_COOLDOWN, user.id)
    if cache.get(cooldown_key):
        raise OTPCooldownError("Please wait before requesting another code.")

    auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.MOBILE
    ).first()

    if not auth_method:
        raise PhoneChangeInvalidError("Please add phone number")

    if not auth_method.is_verified:
        raise PhoneNotVerifiedError("Please verify your phone number")

    old_phone_number = User.objects.filter(id=user.id).first().phone_number

    if old_phone_number == new_phone_number:
        raise SamePhoneNumberError("Please enter different phone number")

    # Invalidate any pending change tokens from a previous, abandoned attempt
    VerificationToken.objects.filter(
        auth_method=auth_method,
        type__in=[
            verification_type.PHONE_CHANGE_OLD_TYPE,
            verification_type.PHONE_CHANGE_NEW_TYPE,
        ],
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())

    old_otp = otp._generate_otp()
    new_otp = otp._generate_otp()
    expires_at = timezone.now() + timedelta(minutes=PHONE_CHANGE_TTL_MINUTES)

    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PHONE_CHANGE_OLD_TYPE,
        token_hash=token.hash_token(old_otp),
        expires_at=expires_at,
    )
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PHONE_CHANGE_NEW_TYPE,
        token_hash=token.hash_token(new_otp),
        expires_at=expires_at,
    )

    # New number has nowhere to live in the DB until confirmed
    cache.set(
        get_cool_down(cooldown.PHONE_CHANGE_PENDING, user.id),
        new_phone_number,
        timeout=PHONE_CHANGE_TTL_MINUTES * 60,
    )
    cache.set(cooldown_key, True, timeout=phone.OTP_RESEND_COOLDOWN_SECONDS)
    cache.delete(get_cool_down(cooldown.PHONE_CHANGE_ATTEMPTS, user.id))

    send_otp_sms_task.delay(user.id, old_otp)  # defaults to user.phone_number
    send_otp_sms_task.delay(user.id, new_otp, override_phone_number=new_phone_number)
