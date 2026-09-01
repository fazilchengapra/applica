import hashlib
import secrets
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from app.apps.users.models import User
from app.apps.authentication.models.auth_method import AuthMethod

from ...models import VerificationToken
from ...constants import verification_type, cooldown, email
from ...utils.cooldown import get_cool_down
from ...utils import token

from ...exceptions.account import UserNotFoundError
from ...exceptions.email import EmailAlreadyVerifiedError
from ...exceptions.token import TokenRequestCooldownError
from app.apps.common.exceptions import UnexpectedError

from ...tasks import send_email_verification_task

# notification
from app.apps.notifications.services.account_service import notify_account_verification


def request_verification(user_mail) -> None:
    try:
        user = User.objects.get(email=user_mail, is_active=True)
    except User.DoesNotExist:
        raise UserNotFoundError("User not found")

    auth_method = AuthMethod.objects.filter(
        user=user.id, provider=AuthMethod.EMAIL
    ).first()

    if not auth_method:
        raise UnexpectedError("Unexpected error occurred")

    if user.is_email_verified:
        raise EmailAlreadyVerifiedError("This email account is already verified.")

    cooldown_key = get_cool_down(cooldown.EMAIL_CHANGE_COOLDOWN, user.id)
    if cache.get(cooldown_key):
        raise TokenRequestCooldownError(
            "Please wait before requesting another verification email."
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = token.hash_token(raw_token)
    expires_at = timezone.now() + timedelta(
        minutes=email.EMAIL_VERIFY_TOKEN_TTL_MINUTES
    )

    with transaction.atomic():

        # invalidate previous un used tokens
        VerificationToken.objects.filter(
            user=user,
            type=verification_type.EMAIL_TYPE,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        VerificationToken.objects.create(
            user=user,
            auth_method=auth_method,
            token_hash=token_hash,
            type=verification_type.EMAIL_TYPE,
            expires_at=expires_at,
        )

        transaction.on_commit(
            lambda: notify_account_verification(user.id, user.email, raw_token)
        )

    cache.set(cooldown_key, True, email.EMAIL_VERIFY_COOLDOWN_SECONDS)
