import pytest
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

from app.apps.authentication.constants import verification_type
from app.apps.authentication.constants import cooldown as cooldown_constants
from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.email import EmailNotVerifiedError
from app.apps.authentication.exceptions.token import (
    TokenExpiredError,
    TokenInvalidError,
)
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.services.password.change_pass_service import (
    change_password,
)
from app.apps.authentication.services.password.forgot_password_service import (
    request_reset,
)
from app.apps.authentication.services.password.reset_password_service import (
    reset_password,
)
from app.apps.authentication.tasks import send_password_reset_email_task
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.authentication.utils.cooldown import get_cool_down
from app.apps.authentication.utils import token as token_utils
from app.apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


# ---------- request_reset ----------


def test_request_reset_unknown_email_raises_user_not_found():
    with pytest.raises(UserNotFoundError):
        request_reset("nobody@example.com")


def test_request_reset_inactive_user_raises_user_not_found():
    user = UserFactory(is_active=False, email="inactive@example.com")

    with pytest.raises(UserNotFoundError):
        request_reset(user.email)


def test_request_reset_no_email_auth_method_return_400():
    user = UserFactory(email="no-auth-method@example.com")

    with pytest.raises(EmailNotVerifiedError):
        request_reset(user.email)


def test_request_reset_unverified_email_raises_email_not_verified():
    user = UserFactory(email="unverified@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)

    with pytest.raises(EmailNotVerifiedError):
        request_reset(user.email)


def test_request_reset_success_creates_token_and_schedules_email(
    django_capture_on_commit_callbacks, mocker
):
    user = UserFactory(email="reset-me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    mock_delay = mocker.patch.object(send_password_reset_email_task, "delay")

    with django_capture_on_commit_callbacks(execute=True):
        request_reset(user.email)

    assert VerificationToken.objects.filter(
        user=user, type=verification_type.PASSWORD_RESET_TYPE, used_at__isnull=True
    ).exists()
    mock_delay.assert_called_once()
    assert mock_delay.call_args.args[0] == user.id


def test_request_reset_respects_cooldown_and_silently_drops(mocker):
    user = UserFactory(email="cooldown@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    mock_delay = mocker.patch.object(send_password_reset_email_task, "delay")

    request_reset(user.email)
    mock_delay.reset_mock()

    # second call within cooldown window: no exception, but also no new token/email
    request_reset(user.email)

    mock_delay.assert_not_called()


def test_request_reset_invalidates_previous_outstanding_token(mocker):
    user = UserFactory(email="reinvalidate@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    mocker.patch.object(send_password_reset_email_task, "delay")

    request_reset(user.email)
    first_token = VerificationToken.objects.get(
        user=user, type=verification_type.PASSWORD_RESET_TYPE
    )

    # bypass cooldown to simulate a second legitimate request later
    cache.delete(get_cool_down(cooldown_constants.PASSWORD_RESET_COOLDOWN, user.id))
    request_reset(user.email)

    first_token.refresh_from_db()
    assert first_token.used_at is not None


# ---------- reset_password ----------


def test_reset_password_invalid_token_raises():
    with pytest.raises(TokenInvalidError):
        reset_password(raw_token="not-a-real-token", new_password="NewPass123!")


def test_reset_password_expired_token_raises():
    user = UserFactory()
    auth_method = AuthMethodFactory(
        user=user, provider=AuthMethod.EMAIL, is_verified=True
    )
    raw_token = "expired-raw-token"
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PASSWORD_RESET_TYPE,
        token_hash=token_utils.hash_token(raw_token),
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    with pytest.raises(TokenExpiredError):
        reset_password(raw_token=raw_token, new_password="NewPass123!")


def test_reset_password_success_sets_new_password_and_marks_token_used():
    user = UserFactory()
    auth_method = AuthMethodFactory(
        user=user, provider=AuthMethod.EMAIL, is_verified=True
    )
    raw_token = "valid-raw-token"
    vt = VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PASSWORD_RESET_TYPE,
        token_hash=token_utils.hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    reset_password(raw_token=raw_token, new_password="NewPass123!")

    user.refresh_from_db()
    vt.refresh_from_db()
    assert user.check_password("NewPass123!")
    assert vt.used_at is not None


def test_reset_password_already_used_token_raises_invalid():
    user = UserFactory()
    auth_method = AuthMethodFactory(
        user=user, provider=AuthMethod.EMAIL, is_verified=True
    )
    raw_token = "already-used-token"
    VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PASSWORD_RESET_TYPE,
        token_hash=token_utils.hash_token(raw_token),
        expires_at=timezone.now() + timedelta(minutes=30),
        used_at=timezone.now(),
    )

    with pytest.raises(TokenInvalidError):
        reset_password(raw_token=raw_token, new_password="NewPass123!")


# ---------- change_password ----------


def test_change_password_wrong_old_password_raises_value_error():
    user = UserFactory()

    with pytest.raises(ValueError):
        change_password(user=user, old_password="wrong", new_password="NewPass123!")


def test_change_password_same_as_old_raises_value_error():
    user = UserFactory()

    with pytest.raises(ValueError):
        change_password(
            user=user, old_password=DEFAULT_PASSWORD, new_password=DEFAULT_PASSWORD
        )


def test_change_password_success():
    user = UserFactory()

    change_password(
        user=user, old_password=DEFAULT_PASSWORD, new_password="NewPass123!"
    )

    user.refresh_from_db()
    assert user.check_password("NewPass123!")
