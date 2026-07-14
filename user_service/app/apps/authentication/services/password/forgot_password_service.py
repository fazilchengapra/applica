import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from app.apps.users.models import User
from app.apps.authentication.models import VerificationToken
from app.apps.authentication.constants import verification_type
from app.apps.authentication.tasks import send_password_reset_email_task
from ...exceptions.account import UserNotFoundError
from ...exceptions.email import EmailNotVerifiedError

from app.apps.authentication.models import AuthMethod

from ...constants import token as token_const, cooldown
from ...utils.cooldown import get_cool_down
from ...utils import token


def request_reset(email: str) -> None:

    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        raise UserNotFoundError("User not found")

    auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.EMAIL
    ).first()

    if not auth_method.is_verified or not auth_method.is_active:
        raise EmailNotVerifiedError("Email is not verified or inactive login method")

    cooldown_key = get_cool_down(cooldown.PASSWORD_RESET_COOLDOWN, user.id)
    if cache.get(cooldown_key):
        return  # silently drop — rate limited

    raw_token = secrets.token_urlsafe(32)
    token_hash = token.hash_token(raw_token)
    expires_at = timezone.now() + timedelta(minutes=token_const.RESET_TOKEN_TTL_MINUTES)

    with transaction.atomic():
        # invalidate any previous outstanding reset tokens for this user
        VerificationToken.objects.filter(
            user=user,
            type=verification_type.PASSWORD_RESET_TYPE,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        VerificationToken.objects.create(
            user=user,
            token_hash=token_hash,
            type=verification_type.PASSWORD_RESET_TYPE,
            expires_at=expires_at,
            auth_method=auth_method,
        )
        transaction.on_commit(
            lambda: send_password_reset_email_task.delay(user.id, raw_token)
        )

    cache.set(cooldown_key, True, token_const.RESET_COOLDOWN_SECONDS)
