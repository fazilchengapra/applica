import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_refresh_without_cookie_returns_401(client):
    response = client.post("/api/v1/auth/token/refresh/")
    assert response.status_code == 401


def test_refresh_with_invalid_token_returns_401(client):
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = "not-a-real-token"

    response = client.post("/api/v1/auth/token/refresh/")

    assert response.status_code == 401


def test_refresh_with_valid_token_sets_new_access_cookie(client):
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = str(refresh)

    response = client.post("/api/v1/auth/token/refresh/")

    assert response.status_code == 200
    access_cookie = response.cookies.get(settings.ACCESS_TOKEN_COOKIE)
    assert access_cookie is not None
    assert access_cookie.value


def test_refresh_does_not_rotate_or_set_new_refresh_cookie(client):
    """
    Per project convention: ROTATE_REFRESH_TOKENS=False — refresh is a
    fixed 7-day credential, this endpoint should only ever set a new
    access_token cookie, never a new refresh_token cookie.
    """
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = str(refresh)

    response = client.post("/api/v1/auth/token/refresh/")

    assert settings.REFRESH_TOKEN_COOKIE not in response.cookies


def test_refresh_with_blacklisted_token_returns_401(client):
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    refresh.blacklist()
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = str(refresh)

    response = client.post("/api/v1/auth/token/refresh/")

    assert response.status_code == 401