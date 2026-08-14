from django.core.cache import cache
from django.utils import timezone
from django.db import transaction

from app.apps.authentication.constants import phone, verification_type

from app.apps.authentication.utils import token as tokens
from app.apps.authentication.utils.cooldown import get_cool_down

from app.apps.authentication.constants import cooldown

from ...exceptions.phone import PhoneChangeInvalidError
from ...exceptions.otp import OTPLockedError

# notification
from app.apps.notifications.services.helper.phone_notification_helper import (
    phone_number_change_notification_helper,
)
from app.apps.notifications.tasks import publish_notification_event_task


def verify_phone_change(user, *, old_code: str, new_code: str) -> None:
    pending_key = get_cool_down(cooldown.PHONE_CHANGE_PENDING, user.id)
    new_phone_number = cache.get(pending_key)
    if new_phone_number is None:
        raise PhoneChangeInvalidError(
            "No pending phone change found. Request a new code."
        )

    attempts_key = get_cool_down(cooldown.PHONE_CHANGE_ATTEMPTS, user.id)
    attempts = cache.get(attempts_key, 0)
    if attempts >= phone.OTP_MAX_ATTEMPTS:
        raise OTPLockedError("Too many incorrect attempts. Request a new code.")

    old_token = tokens._get_valid_token(user, verification_type.PHONE_CHANGE_OLD_TYPE)
    new_token = tokens._get_valid_token(user, verification_type.PHONE_CHANGE_NEW_TYPE)

    if old_token is None or new_token is None:
        raise PhoneChangeInvalidError("Code expired or not found. Request a new one.")

    old_ok = old_token.token_hash == tokens.hash_token(old_code)
    new_ok = new_token.token_hash == tokens.hash_token(new_code)

    if not (old_ok and new_ok):
        cache.set(attempts_key, attempts + 1, timeout=phone.OTP_TTL_MINUTES * 60)
        raise PhoneChangeInvalidError("One or both codes are incorrect.")

    with transaction.atomic():
        old_token.used_at = timezone.now()
        old_token.save(update_fields=["used_at"])

        new_token.used_at = timezone.now()
        new_token.save(update_fields=["used_at"])

        new_token.auth_method.last_used_at = timezone.now()
        new_token.auth_method.save(update_fields=["last_used_at"])

        old_number = user.phone_number

        user.phone_number = new_phone_number
        user.is_phone_verified = True
        user.save(update_fields=["phone_number", "is_phone_verified"])

        data = phone_number_change_notification_helper(
            user=user, new_phone=new_phone_number, old_phone=old_number
        )
        transaction.on_commit(lambda: publish_notification_event_task.delay(**data))

    cache.delete(attempts_key)
    cache.delete(pending_key)
    cache.delete(f"phone_change:cooldown:{user.id}")
