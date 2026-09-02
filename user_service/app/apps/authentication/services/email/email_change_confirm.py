from ...utils import token
from django.db import transaction
from app.apps.authentication.models import VerificationToken
from ...constants import verification_type, cooldown, email
from django.utils import timezone
from app.apps.authentication.exceptions.email import (
    EmailChangeTokenInvalidError,
    EmailInUseError,
)
from app.apps.notifications.constants.notification_type import NotificationType
from django.core.cache import cache
from ...utils.cooldown import get_cool_down
from app.apps.users.models import User

# notification
from app.apps.notifications.services.account_service import notify_email_changed

# utils
from app.apps.common.utils.mask import mask_email


def confirm_email_change(user, raw_token: str) -> bool:
    """Returns True once both old and new email have confirmed and the swap is complete."""
    token_hash = token.hash_token(raw_token)

    verification_token = VerificationToken.objects.filter(
        user=user,
        type__in=[
            verification_type.EMAIL_CHANGE_OLD_TYPE,
            verification_type.EMAIL_CHANGE_NEW_TYPE,
        ],
        token_hash=token_hash,
        used_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()

    if not verification_token:
        raise EmailChangeTokenInvalidError("Invalid or expired token.")

    verification_token.used_at = timezone.now()
    verification_token.save(update_fields=["used_at"])

    if verification_token.type == verification_type.EMAIL_CHANGE_OLD_TYPE:
        cache.set(
            get_cool_down(cooldown.EMAIL_CHANGE_OLD, user.id),
            True,
            timeout=email.EMAIL_CHANGE_TOKEN_TTL_MINUTES * 60,
        )
    else:
        cache.set(
            get_cool_down(cooldown.EMAIL_CHANGE_NEW, user.id),
            True,
            timeout=email.EMAIL_CHANGE_TOKEN_TTL_MINUTES * 60,
        )

    old_verified = cache.get(get_cool_down(cooldown.EMAIL_CHANGE_OLD, user.id))
    new_verified = cache.get(get_cool_down(cooldown.EMAIL_CHANGE_NEW, user.id))

    if not (old_verified and new_verified):
        return False

    new_email = cache.get(get_cool_down(cooldown.EMAIL_CHANGE_PENDING, user.id))
    if not new_email:
        raise EmailChangeTokenInvalidError("Email change request expired.")

    if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
        raise EmailInUseError("This email is already in use.")

    old_mail = user.email

    user.email = new_email
    user.is_email_verified = True
    user.save(update_fields=["email", "is_email_verified"])

    cache.delete(get_cool_down(cooldown.EMAIL_CHANGE_OLD, user.id))
    cache.delete(get_cool_down(cooldown.EMAIL_CHANGE_NEW, user.id))

    transaction.on_commit(lambda: notify_email_changed(new_email, mask_email(old_mail), user.id))
    return True
