from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from app.apps.users.models import User
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.constants import verification_type

from ...constants import token, cooldown
from ...utils.cooldown import get_cool_down
from ...utils import token
from ...exceptions.token import TokenInvalidError, TokenExpiredError

# notifications
from app.apps.authentication.services.password import reset_password_service

def reset_password(raw_token: str, new_password: str) -> None:

    token_hash = token.hash_token(raw_token)

    try:
        record = VerificationToken.objects.select_related("user").get(
            token_hash=token_hash,
            type=verification_type.PASSWORD_RESET_TYPE,
            used_at__isnull=True,
        )
    except VerificationToken.DoesNotExist:
        raise TokenInvalidError("This reset link is invalid or has already been used.")

    if record.expires_at < timezone.now():
        raise TokenExpiredError(
            "This reset link has expired. Please request a new one."
        )

    with transaction.atomic():
        user = record.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        record.used_at = timezone.now()
        record.save(update_fields=["used_at"])

        reset_password_service(user=user)

    cache.delete(get_cool_down(cooldown.PASSWORD_RESET_COOLDOWN, user.id))
