import pytest
from django.core.cache import cache

from app.apps.authentication.exceptions.email import (
    EmailInUseError,
    EmailChangeInvalidError,
    EmailNotVerifiedError,
    SameEmailError,
    EmailChangeTokenInvalidError,
)
from app.apps.authentication.exceptions.token import TokenRequestCooldownError
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.constants import verification_type
from app.apps.authentication.services.email.email_change_confirm import confirm_email_change
from app.apps.authentication.services.email.email_change_request import request_email_change
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


# ---------- request_email_change ----------

def test_request_email_change_email_already_in_use_raises():
    UserFactory(email="taken@example.com")
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    with pytest.raises(EmailInUseError):
        request_email_change(user, "taken@example.com")


def test_request_email_change_no_auth_method_raises_invalid():
    user = UserFactory(email="me@example.com")

    with pytest.raises(EmailChangeInvalidError):
        request_email_change(user, "new@example.com")


def test_request_email_change_unverified_auth_method_raises():
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)

    with pytest.raises(EmailNotVerifiedError):
        request_email_change(user, "new@example.com")


def test_request_email_change_same_email_raises():
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    with pytest.raises(SameEmailError):
        request_email_change(user, "ME@example.com")


def test_request_email_change_success_creates_both_tokens_and_sends_both_emails(mocker):
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    mock_delay = mocker.patch.object(send_email_verification_task, "delay")

    request_email_change(user, "new@example.com")

    assert VerificationToken.objects.filter(
        user=user, type=verification_type.EMAIL_CHANGE_OLD_TYPE, used_at__isnull=True
    ).exists()
    assert VerificationToken.objects.filter(
        user=user, type=verification_type.EMAIL_CHANGE_NEW_TYPE, used_at__isnull=True
    ).exists()
    assert mock_delay.call_count == 2


def test_request_email_change_respects_cooldown(mocker):
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    mocker.patch.object(send_email_verification_task, "delay")

    request_email_change(user, "new@example.com")

    with pytest.raises(TokenRequestCooldownError):
        request_email_change(user, "another@example.com")


# ---------- confirm_email_change ----------

def _start_change(user, new_email="new@example.com", mocker=None):
    from app.apps.authentication.services.email.email_change_request import (
        request_email_change,
    )

    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    old_token = VerificationToken.objects.none()
    request_email_change(user, new_email)
    old = VerificationToken.objects.get(user=user, type=verification_type.EMAIL_CHANGE_OLD_TYPE)
    new = VerificationToken.objects.get(user=user, type=verification_type.EMAIL_CHANGE_NEW_TYPE)
    return old, new


def test_confirm_email_change_invalid_token_raises():
    user = UserFactory(email="me@example.com")

    with pytest.raises(EmailChangeTokenInvalidError):
        confirm_email_change(user, "not-a-real-token")


def test_confirm_email_change_only_old_confirmed_returns_incomplete(mocker):
    user = UserFactory(email="me@example.com")
    mocker.patch.object(send_email_verification_task, "delay")
    old, new = _start_change(user)

    # we only know the hash, not the raw token — recreate one deliberately
    # by regenerating through the service isn't possible post-hash, so
    # instead create a fresh known raw token bound to the same type for testing
    raw_old = "known-old-raw-token"
    old.token_hash = token_utils.hash_token(raw_old)
    old.save(update_fields=["token_hash"])

    result = confirm_email_change(user, raw_old)

    assert result is False
    user.refresh_from_db()
    assert user.email == "me@example.com"  # unchanged so far


def test_confirm_email_change_both_confirmed_completes_swap(mocker):
    user = UserFactory(email="me@example.com")
    mocker.patch.object(send_email_verification_task, "delay")
    old, new = _start_change(user, new_email="new@example.com")

    raw_old = "known-old-raw-token-2"
    raw_new = "known-new-raw-token-2"
    old.token_hash = token_utils.hash_token(raw_old)
    old.save(update_fields=["token_hash"])
    new.token_hash = token_utils.hash_token(raw_new)
    new.save(update_fields=["token_hash"])

    first_result = confirm_email_change(user, raw_old)
    assert first_result is False

    second_result = confirm_email_change(user, raw_new)
    assert second_result is True

    user.refresh_from_db()
    assert user.email == "new@example.com"
    assert user.is_email_verified is True


def test_confirm_email_change_used_token_raises_invalid(mocker):
    user = UserFactory(email="me@example.com")
    mocker.patch.object(send_email_verification_task, "delay")
    old, new = _start_change(user)

    raw_old = "already-used-raw"
    old.token_hash = token_utils.hash_token(raw_old)
    old.used_at = None
    old.save(update_fields=["token_hash"])

    confirm_email_change(user, raw_old)  # consumes it

    with pytest.raises(EmailChangeTokenInvalidError):
        confirm_email_change(user, raw_old)  # reuse attempt