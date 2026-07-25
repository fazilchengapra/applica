import pytest
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

from app.apps.authentication.constants import verification_type
from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.email import (
    EmailAlreadyVerifiedError,
    EmailVerificationInvalidError,
)
from app.apps.authentication.exceptions.token import TokenRequestCooldownError
from app.apps.common.exceptions import UnexpectedError
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.services.email.email_verify import verify_email
from app.apps.authentication.services.email.email_verify_req import request_verification
from app.apps.authentication.tasks import send_email_verification_task
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.authentication.utils import token as token_utils
from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


# ---------- request_verification ----------

def test_request_verification_unknown_email_raises_user_not_found():
    with pytest.raises(UserNotFoundError):
        request_verification("nobody@example.com")


def test_request_verification_no_auth_method_raises_unexpected_error():
    user = UserFactory(email="no-method@example.com")

    with pytest.raises(UnexpectedError):
        request_verification(user.email)


def test_request_verification_already_verified_raises():
    user = UserFactory(email="already@example.com", is_email_verified=True)
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    with pytest.raises(EmailAlreadyVerifiedError):
        request_verification(user.email)


def test_request_verification_success_creates_token_and_sends_email(
    django_capture_on_commit_callbacks, mocker
):
    user = UserFactory(email="verify-me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)
    mock_delay = mocker.patch.object(send_email_verification_task, "delay")

    with django_capture_on_commit_callbacks(execute=True):
        request_verification(user.email)

    assert VerificationToken.objects.filter(
        user=user, type=verification_type.EMAIL_TYPE, used_at__isnull=True
    ).exists()
    mock_delay.assert_called_once()


def test_request_verification_respects_cooldown():
    user = UserFactory(email="cooldown@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)

    request_verification(user.email)

    with pytest.raises(TokenRequestCooldownError):
        request_verification(user.email)


# ---------- verify_email ----------

def test_verify_email_invalid_token_raises():
    with pytest.raises(EmailVerificationInvalidError):
        verify_email(raw_token="not-a-real-token")


def test_verify_email_expired_token_raises():
    user = UserFactory()
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)
    raw_token = "expired-token"
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.EMAIL_TYPE,
        token_hash=token_utils.hash_token(raw_token),
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    with pytest.raises(EmailVerificationInvalidError):
        verify_email(raw_token=raw_token)


def test_verify_email_success_marks_user_and_auth_method_verified():
    user = UserFactory()
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)
    raw_token = "valid-token"
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.EMAIL_TYPE,
        token_hash=token_utils.hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    verify_email(raw_token=raw_token)

    user.refresh_from_db()
    auth_method.refresh_from_db()
    assert user.is_email_verified is True
    assert auth_method.is_verified is True


def test_verify_email_already_used_token_raises():
    user = UserFactory()
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)
    raw_token = "used-token"
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.EMAIL_TYPE,
        token_hash=token_utils.hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=30),
        used_at=timezone.now(),
    )

    with pytest.raises(EmailVerificationInvalidError):
        verify_email(raw_token=raw_token)