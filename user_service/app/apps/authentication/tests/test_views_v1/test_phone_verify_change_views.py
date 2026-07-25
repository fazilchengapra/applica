import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.tests.factories import AuthMethodFactory
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


def test_request_phone_otp_initial_verification_expect_200(client):

    user = UserFactory(phone_number="+919876500301")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=False)
    _authenticate_via_cookie(client, user)

    response = client.post("/api/v1/auth/phone/otp/request/")

    assert response.status_code == 200


def test_request_phone_change_no_auth_method_currently_expect_400(client):
    """
    expect 400 bad request with add phone number error message
    """
    user = UserFactory(phone_number="+919876500302")
    _authenticate_via_cookie(client, user)

    response = client.post(
        "/api/v1/auth/phone/change/request/",
        {"new_phone_number": "+919876500399"},
        format="json",
    )

    assert response.status_code == 400


def test_verify_phone_change_success_returns_200(client, mocker):
    from app.apps.authentication.services.phone.request_phone_change import (
        request_phone_change,
    )
    from app.apps.authentication.models.verification_token import VerificationToken
    from app.apps.authentication.constants import verification_type
    from app.apps.authentication.utils import token as token_utils

    user = UserFactory(phone_number="+919876500303")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    _authenticate_via_cookie(client, user)
    mocker.patch(
        "app.apps.authentication.services.phone.request_phone_change.send_otp_sms_task.delay"
    )

    request_phone_change(user, "+919876500400")
    old = VerificationToken.objects.get(user=user, type=verification_type.PHONE_CHANGE_OLD_TYPE)
    new = VerificationToken.objects.get(user=user, type=verification_type.PHONE_CHANGE_NEW_TYPE)
    old.token_hash = token_utils.hash_token("333333")
    old.save(update_fields=["token_hash"])
    new.token_hash = token_utils.hash_token("444444")
    new.save(update_fields=["token_hash"])

    response = client.post(
        "/api/v1/auth/phone/change/verify/",
        {"old_code": "333333", "new_code": "444444"},
        format="json",
    )

    assert response.status_code == 200