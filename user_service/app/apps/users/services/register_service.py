import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

# models
from app.apps.users.models import User
from app.apps.authentication.models import AuthMethod, VerificationToken
from app.apps.profiles.models import Profile

# verification type
from app.apps.authentication.constants import verification_type

# constants
VERIFICATION_TOKEN_TTL_MINUTES = 30

# task
from app.apps.authentication.tasks import send_email_verification_task

# notification
from app.apps.notifications.services.welcome_notification import send_welcome as send_welcome_notification
from app.apps.notifications.services import account_service

def _generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


@transaction.atomic
def register_user(*, first_name, last_name, email, phone_number, password, **kwargs) -> User:

    user = User.objects.create_user(
        email=email,
        phone_number=phone_number,
        password=password,
    )

    Profile.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
        display_name=first_name,
    )

    auth_method = AuthMethod.objects.create(
        user=user,
        provider=AuthMethod.EMAIL
    )

    AuthMethod.objects.create(
        user=user,
        provider = AuthMethod.MOBILE
    )

    raw_token = _generate_raw_token()
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.EMAIL_TYPE,
        token_hash=_hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=VERIFICATION_TOKEN_TTL_MINUTES),
    )
    # send_welcome_notification(user=user) ## TODO
    account_service.notify_account_verification(user.id, user.email, raw_token)
    return user