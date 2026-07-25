import pytest
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from app.apps.authentication.constants import verification_type
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.tasks import send_otp_sms_task
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.authentication.utils import token as token_utils
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


def _create_phone_otp_token(user, auth_method, raw_code="654321"):
    return VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PHONE_TYPE,
        token_hash=token_utils.hash_token(raw_code),
        expires_at=timezone.now() + timedelta(minutes=5),
    )


def test_request_login_otp_unknown_phone_returns_400(client):
    response = client.post(
        "/api/v1/auth/phone/login/request/",
        {"phone_number": "+919999999997"},
        format="json",
    )
    assert response.status_code == 400


def test_request_login_otp_success_returns_200(client, mocker):
    user = UserFactory(phone_number="+919876500030", is_phone_verified=True)
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    mocker.patch.object(send_otp_sms_task, "delay")

    response = client.post(
        "/api/v1/auth/phone/login/request/",
        {"phone_number": str(user.phone_number)},
        format="json",
    )
    assert response.status_code == 200


def test_verify_login_otp_success_sets_cookies(client):
    user = UserFactory(phone_number="+919876500031")
    auth_method = AuthMethodFactory(
        user=user, provider=AuthMethod.MOBILE, is_verified=True
    )
    _create_phone_otp_token(user, auth_method, raw_code="654321")

    response = client.post(
        "/api/v1/auth/phone/login/verify/",
        {"phone_number": str(user.phone_number), "code": "654321"},
        format="json",
    )

    assert response.status_code == 200
    assert settings.ACCESS_TOKEN_COOKIE in response.cookies
    assert settings.REFRESH_TOKEN_COOKIE in response.cookies


def test_verify_login_otp_wrong_code_returns_400(client):
    user = UserFactory(phone_number="+919876500032")
    auth_method = AuthMethodFactory(
        user=user, provider=AuthMethod.MOBILE, is_verified=True
    )
    _create_phone_otp_token(user, auth_method, raw_code="654321")

    response = client.post(
        "/api/v1/auth/phone/login/verify/",
        {"phone_number": str(user.phone_number), "code": "000000"},
        format="json",
    )
    assert response.status_code == 400
