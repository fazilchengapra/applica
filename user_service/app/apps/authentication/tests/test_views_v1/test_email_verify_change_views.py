# core imports
import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta

# models
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.users.tests.factories import UserFactory

# service
from app.apps.authentication.services.email.email_change_confirm import confirm_email_change

# utils
from app.apps.authentication.utils import token as token_utils
from app.apps.authentication.utils.cooldown import get_cool_down

# constants
from app.apps.authentication.constants import verification_type
from app.apps.authentication.constants import cooldown

# tasks
from app.apps.authentication.tasks import send_email_verification_task

# factory
from ..factories import AuthMethodFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def _authenticate_via_cookie(client, user):
    access_token = str(RefreshToken.for_user(user).access_token)
    client.cookies[settings.ACCESS_TOKEN_COOKIE] = access_token
    return client


# ---------- request verification ----------

def test_request_email_verification_unknown_email_returns_404(client):
    response = client.post(
        "/api/v1/auth/email/verify/request/",
        {"email": "nobody@example.com"},
        format="json",
    )
    assert response.status_code == 404


def test_request_email_verification_no_auth_method_returns_500(client):
    """
    Confirms the UnexpectedError path really does surface as a 500
    through the real HTTP layer for a user with no EMAIL AuthMethod.
    """
    user = UserFactory(email="no-method@example.com")

    response = client.post(
        "/api/v1/auth/email/verify/request/", {"email": user.email}, format="json"
    )
    assert response.status_code == 500


def test_request_email_verification_success_returns_200(client, mocker):
    user = UserFactory(email="verify@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)
    mocker.patch.object(send_email_verification_task, "delay")

    response = client.post(
        "/api/v1/auth/email/verify/request/", {"email": user.email}, format="json"
    )
    assert response.status_code == 200


# ---------- change request ----------

def test_email_change_request_requires_authentication(client):
    response = client.post(
        "/api/v1/auth/email/change/request/",
        {"new_email": "new@example.com"},
        format="json",
    )
    assert response.status_code == 401


def test_email_change_request_success_returns_200(client, mocker):
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    _authenticate_via_cookie(client, user)
    mocker.patch.object(send_email_verification_task, "delay")

    response = client.post(
        "/api/v1/auth/email/change/request/",
        {"new_email": "new@example.com"},
        format="json",
    )
    assert response.status_code == 200


def test_email_change_request_same_email_returns_400(client):
    user = UserFactory(email="me@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    _authenticate_via_cookie(client, user)

    response = client.post(
        "/api/v1/auth/email/change/request/",
        {"new_email": "me@example.com"},
        format="json",
    )
    assert response.status_code == 400

# def test_confirm_email_change_success_updates_email_and_sends_notification(mocker):
#     user = UserFactory(email="old@example.com")

#     mock_notify = mocker.patch(
#         "app.apps.notifications.services.email_notification.email_change_notification"
#     )

#     raw_token = "new-token"

#     auth_method = AuthMethodFactory(
#         user=user,
#         is_verified=False,
#         is_active=False,
#     )

#     VerificationToken.objects.create(
#         user=user,
#         auth_method=auth_method,
#         type=verification_type.EMAIL_CHANGE_NEW_TYPE,
#         token_hash=token_utils.hash_token(raw_token),
#     )

#     # Simulate that the old-email confirmation already happened.
#     cache.set(get_cool_down(cooldown.EMAIL_CHANGE_OLD, user.id), True)
#     cache.set(
#         get_cool_down(cooldown.EMAIL_CHANGE_PENDING, user.id),
#         "new@example.com",
#     )

#     result = confirm_email_change(user=user, raw_token=raw_token)

#     user.refresh_from_db()

#     assert result is True
#     assert user.email == "new@example.com"
#     assert user.is_email_verified is True

#     # cache cleared
#     assert cache.get(get_cool_down(cooldown.EMAIL_CHANGE_OLD, user.id)) is None
#     assert cache.get(get_cool_down(cooldown.EMAIL_CHANGE_NEW, user.id)) is None

#     mock_notify.assert_called_once_with(
#         user=user,
#         new_email="new@example.com",
#         old_email="old@example.com",
#     )