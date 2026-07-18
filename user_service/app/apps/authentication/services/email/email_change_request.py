from django.core.cache import cache

from app.apps.users.models import User
from ...exceptions.email import (
    EmailInUseError,
    EmailChangeInvalidError,
    EmailNotVerifiedError,
    SameEmailError,
)
from ...exceptions.token import TokenRequestCooldownError
from ...utils.cooldown import get_cool_down
from ...constants import cooldown, verification_type
from ...models import AuthMethod, VerificationToken
from ...utils import token
from datetime import timedelta
from django.utils import timezone
from ...constants import email
from app.apps.authentication.tasks import send_email_verification_task


def request_email_change(user, new_email: str) -> None:
    new_email = new_email.strip().lower()

    if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
        raise EmailInUseError("This email is already in use.")

    cooldown_key = get_cool_down(cooldown.EMAIL_CHANGE_COOLDOWN, user.id)
    if cache.get(cooldown_key):
        raise TokenRequestCooldownError("Please wait before requesting another code.")

    auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.EMAIL
    ).first()

    if not auth_method:
        raise EmailChangeInvalidError("Please add an email address")

    if not auth_method.is_verified:
        raise EmailNotVerifiedError("Please verify your email address")

    old_email = User.objects.filter(id=user.id).first().email

    if old_email.lower() == new_email:
        raise SameEmailError("Please enter a different email address")

    # Invalidate any pending change tokens from a previous, abandoned attempt
    VerificationToken.objects.filter(
        auth_method=auth_method,
        type__in=[
            verification_type.EMAIL_CHANGE_OLD_TYPE,
            verification_type.EMAIL_CHANGE_NEW_TYPE,
        ],
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())

    raw_old_token = token.generate_raw_token()
    raw_new_token = token.generate_raw_token()
    expires_at = timezone.now() + timedelta(minutes=email.EMAIL_CHANGE_TOKEN_TTL_MINUTES)

    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.EMAIL_CHANGE_OLD_TYPE,
        token_hash=token.hash_token(raw_old_token),
        expires_at=expires_at,
    )
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.EMAIL_CHANGE_NEW_TYPE,
        token_hash=token.hash_token(raw_new_token),
        expires_at=expires_at,
    )

    # New address has nowhere to live in the DB until both sides confirm
    cache.set(
        get_cool_down(cooldown.EMAIL_CHANGE_PENDING, user.id),
        new_email,
        timeout=email.EMAIL_CHANGE_TOKEN_TTL_MINUTES * 60,
    )
    cache.set(
        cooldown_key, True, timeout=email.EMAIL_CHANGE_COOLDOWN_SECONDS
    )
    cache.delete(get_cool_down(cooldown.EMAIL_CHANGE_OLD, user.id))
    cache.delete(get_cool_down(cooldown.EMAIL_CHANGE_NEW, user.id))

    send_email_verification_task.delay(
        user.id, raw_old_token, email_change=True
    )  # defaults to user.email
    send_email_verification_task.delay(
        user.id, raw_new_token, email=new_email, email_change=True
    )
