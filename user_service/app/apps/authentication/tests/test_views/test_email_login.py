import pytest
from django.conf import settings
from rest_framework.test import APIClient

from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_login_success_sets_cookies_and_returns_200(client):
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    response = client.post(
        "/api/v1/auth/email/login/",  # will fix once we see real urls.py
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["user"]["email"] == user.email
    assert settings.ACCESS_TOKEN_COOKIE in response.cookies
    assert settings.REFRESH_TOKEN_COOKIE in response.cookies


def test_login_wrong_password_returns_400(client):
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=True)

    response = client.post(
        "/api/v1/auth/email/login/",
        {"email": user.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 400


def test_login_unverified_email_returns_403(client):
    user = UserFactory()
    AuthMethodFactory(user=user, provider=AuthMethod.EMAIL, is_verified=False)

    response = client.post(
        "/api/v1/auth/email/login/",
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )

    assert response.status_code == 403
