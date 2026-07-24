import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def _authenticate_via_cookie(client, user):
    access_token = str(RefreshToken.for_user(user).access_token)
    client.cookies[settings.ACCESS_TOKEN_COOKIE] = access_token
    return client


def test_logout_requires_authentication(client):
    response = client.post("/api/v1/auth/logout/")
    assert response.status_code == 401


def test_logout_blacklists_refresh_token_and_clears_cookies(client):
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    _authenticate_via_cookie(client, user)
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = str(refresh)

    response = client.post("/api/v1/auth/logout/")

    assert response.status_code == 200
    assert BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()

    access_cookie = response.cookies.get(settings.ACCESS_TOKEN_COOKIE)
    refresh_cookie = response.cookies.get(settings.REFRESH_TOKEN_COOKIE)
    assert access_cookie["max-age"] == 0
    assert refresh_cookie["max-age"] == 0


def test_logout_without_refresh_cookie_still_succeeds(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)
    # deliberately no refresh cookie set

    response = client.post("/api/v1/auth/logout/")

    assert response.status_code == 200


def test_logout_with_already_invalid_refresh_token_still_succeeds(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = "garbage-not-a-real-token"

    response = client.post("/api/v1/auth/logout/")

    assert response.status_code == 200


def test_logout_blacklisted_refresh_token_used_again_still_returns_200(client):
    """
    Logging out twice with the same (now-blacklisted) refresh token
    should not error — the view already handles TokenError silently.
    """
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    _authenticate_via_cookie(client, user)
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = str(refresh)

    client.post("/api/v1/auth/logout/")  # first logout, blacklists it

    _authenticate_via_cookie(client, user)
    client.cookies[settings.REFRESH_TOKEN_COOKIE] = str(refresh)
    response = client.post("/api/v1/auth/logout/")  # second attempt, same token

    assert response.status_code == 200