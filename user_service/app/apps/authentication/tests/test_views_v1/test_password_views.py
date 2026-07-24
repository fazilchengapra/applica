import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.authentication.tasks import send_password_reset_email_task
from app.apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory

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


# ---------- forgot password ----------

def test_forgot_password_unknown_email_returns_400(client):
    response = client.post(
        "/api/v1/auth/password/forgot/", {"email": "nobody@example.com"}, format="json"
    )
    assert response.status_code == 400


def test_forgot_password_success_returns_200(client, mocker):
    user = UserFactory(email="forgot@example.com")
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)
    mocker.patch.object(send_password_reset_email_task, "delay")

    response = client.post(
        "/api/v1/auth/password/forgot/", {"email": user.email}, format="json"
    )
    assert response.status_code == 200


def test_forgot_password_no_email_auth_method_expect_err_400(client):
    
    user = UserFactory(email="crash@example.com")

    response = client.post(
        "/api/v1/auth/password/forgot/", {"email": user.email}, format="json"
    )
    assert response.status_code == 400


# ---------- reset password ----------

def test_reset_password_mismatched_confirm_returns_400(client):
    response = client.post(
        "/api/v1/auth/password/reset/",
        {"token": "abc", "new_password": "NewPass123!", "confirm_password": "different"},
        format="json",
    )
    assert response.status_code == 400


def test_reset_password_invalid_token_returns_400(client):
    response = client.post(
        "/api/v1/auth/password/reset/",
        {
            "token": "not-a-real-token",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == 400


# ---------- change password ----------

def test_change_password_requires_authentication(client):
    response = client.post(
        "/api/v1/auth/password/change/",
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == 401


def test_change_password_wrong_old_password_returns_400(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.post(
        "/api/v1/auth/password/change/",
        {
            "old_password": "wrong-password",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == 400


def test_change_password_mismatched_confirm_returns_400(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.post(
        "/api/v1/auth/password/change/",
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": "NewPass123!",
            "confirm_password": "different",
        },
        format="json",
    )
    assert response.status_code == 400


def test_change_password_success_returns_200(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.post(
        "/api/v1/auth/password/change/",
        {
            "old_password": DEFAULT_PASSWORD,
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("NewPass123!")