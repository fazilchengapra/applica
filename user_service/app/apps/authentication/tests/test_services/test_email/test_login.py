import pytest

from app.apps.authentication.services.email.login import login_user
from app.apps.authentication.exceptions.account import (
    UserNotFoundError,
)
from app.apps.authentication.exceptions.authentication import InvalidCredentialsError
from ....exceptions.email import EmailInActiveError
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def test_login_success_returns_tokens_and_user():
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    result = login_user(email=user.email, password=DEFAULT_PASSWORD)

    assert result["user"] == user
    assert result["access"]
    assert result["refresh"]


def test_login_updates_last_login_timestamp():
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    assert user.last_login is None

    login_user(email=user.email, password=DEFAULT_PASSWORD)

    user.refresh_from_db()
    assert user.last_login is not None


def test_login_wrong_password_raises_user_not_found():
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    with pytest.raises(InvalidCredentialsError):
        login_user(email=user.email, password="wrong-password")


def test_login_unknown_email_raises_user_not_found():
    with pytest.raises(InvalidCredentialsError):
        login_user(email="nobody@example.com", password=DEFAULT_PASSWORD)


def test_login_without_verified_email_auth_method_raises_email_inactive():
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)

    with pytest.raises(EmailInActiveError):
        login_user(email=user.email, password=DEFAULT_PASSWORD)


def test_inactive_accounts_to_get_invalid_credentials_err():
    user = UserFactory(is_active=False)
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    with pytest.raises(InvalidCredentialsError):
        login_user(email=user.email, password=DEFAULT_PASSWORD)


def test_login_does_not_update_last_used_at_due_to_provider_mismatch():
    user = UserFactory()
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    assert auth_method.last_used_at is None

    login_user(email=user.email, password=DEFAULT_PASSWORD)

    auth_method.refresh_from_db()
    assert auth_method.last_used_at is None