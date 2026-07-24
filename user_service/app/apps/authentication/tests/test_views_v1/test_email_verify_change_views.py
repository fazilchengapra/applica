import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.authentication.tasks import send_email_verification_task
from app.apps.users.tests.factories import UserFactory

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