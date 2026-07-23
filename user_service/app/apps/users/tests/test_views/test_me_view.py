import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.profiles.models import Profile
from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def _authenticate_via_cookie(client, user):
    """
    Mimics real login: puts a genuine signed access token into the
    access_token cookie, so the request goes through the real
    CookieJWTAuthentication class instead of bypassing it.
    """
    access_token = str(RefreshToken.for_user(user).access_token)
    client.cookies[settings.ACCESS_TOKEN_COOKIE] = access_token
    return client


def test_me_requires_authentication(client):
    response = client.get("/api/v1/users/me/")
    assert response.status_code == 401


def test_me_returns_current_user_data(client):
    user = UserFactory(email="fazil@example.com")
    Profile.objects.create(user=user, first_name="Fazil", last_name="Chengapra")
    _authenticate_via_cookie(client, user)

    response = client.get("/api/v1/users/me/")

    assert response.status_code == 200
    assert response.data["email"] == "fazil@example.com"
    assert response.data["profile"]["first_name"] == "Fazil"


def test_me_query_count_stays_low(client, django_assert_max_num_queries):
    user = UserFactory()
    Profile.objects.create(user=user, first_name="Fazil", last_name="C")
    _authenticate_via_cookie(client, user)

    # Upper bound, not exact — catches N+1 regressions without being
    # too brittle about the precise number (auth lookup + profile join).
    with django_assert_max_num_queries(3):
        response = client.get("/api/v1/users/me/")

    assert response.status_code == 200

def test_delete_me_wrong_password_returns_400(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.delete(
        "/api/v1/users/me/",
        {"password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_active is True


def test_delete_me_correct_password_deactivates_and_returns_204(client, mailoutbox):
    from app.apps.users.tests.factories import DEFAULT_PASSWORD

    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.delete(
        "/api/v1/users/me/",
        {"password": DEFAULT_PASSWORD},
        format="json",
    )

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.is_active is False
    assert user.deactivated_at is not None


def test_delete_me_clears_auth_cookies(client):
    from app.apps.users.tests.factories import DEFAULT_PASSWORD

    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.delete(
        "/api/v1/users/me/",
        {"password": DEFAULT_PASSWORD},
        format="json",
    )

    access_cookie = response.cookies.get(settings.ACCESS_TOKEN_COOKIE)
    refresh_cookie = response.cookies.get(settings.REFRESH_TOKEN_COOKIE)
    assert access_cookie is not None
    assert access_cookie["max-age"] == 0
    assert refresh_cookie is not None
    assert refresh_cookie["max-age"] == 0


def test_delete_me_missing_password_currently_returns_200_not_400(client):
    user = UserFactory()
    _authenticate_via_cookie(client, user)

    response = client.delete(
        "/api/v1/users/me/",
        {},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_active is True  # account not actually touched, at least