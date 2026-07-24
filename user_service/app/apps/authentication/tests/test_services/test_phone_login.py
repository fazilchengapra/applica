import pytest
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

from app.apps.authentication.constants import verification_type
from app.apps.authentication.constants import phone as phone_constants
from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.otp import (
    OTPCooldownError,
    OTPInvalidError,
    OTPLockedError,
)
from app.apps.authentication.exceptions.phone import PhoneNotVerifiedError
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.services.phone.request_login_otp import request_login_otp
from app.apps.authentication.services.phone.verify_login_otp import verify_login_otp
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


def _create_phone_otp_token(user, auth_method, raw_code="654321", expired=False):
    expires_at = (
        timezone.now() - timedelta(minutes=1)
        if expired
        else timezone.now() + timedelta(minutes=5)
    )
    return VerificationToken.objects.create(
        user=user,
        auth_method=auth_method,
        type=verification_type.PHONE_TYPE,
        token_hash=token_utils.hash_token(raw_code),
        expires_at=expires_at,
    )


# ---------- request_login_otp ----------

def test_request_login_otp_unknown_phone_raises_user_not_found():
    with pytest.raises(UserNotFoundError):
        request_login_otp("+919999999999")


def test_request_login_otp_unverified_phone_raises_phone_not_verified():
    user = UserFactory(phone_number="+919876500010")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=False)

    with pytest.raises(PhoneNotVerifiedError):
        request_login_otp(str(user.phone_number))


def test_request_login_otp_success_creates_token_and_schedules_sms(
    django_capture_on_commit_callbacks, mocker
):
    user = UserFactory(phone_number="+919876500011")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    mock_delay = mocker.patch.object(send_otp_sms_task, "delay")

    with django_capture_on_commit_callbacks(execute=True):
        request_login_otp(str(user.phone_number))

    assert VerificationToken.objects.filter(
        user=user, type=verification_type.PHONE_TYPE
    ).exists()
    mock_delay.assert_called_once()
    assert mock_delay.call_args.args[0] == user.id


def test_request_login_otp_respects_cooldown(mocker):
    user = UserFactory(phone_number="+919876500012")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    mocker.patch.object(send_otp_sms_task, "delay")

    request_login_otp(str(user.phone_number))

    with pytest.raises(OTPCooldownError):
        request_login_otp(str(user.phone_number))


def test_request_login_otp_no_mobile_auth_method_currently_crashes(mocker):
    """
    Documents a real bug: a user with zero MOBILE AuthMethod rows causes
    auth_method to resolve to None, and VerificationToken.objects.create()
    fails because auth_method is a required (non-nullable) FK — this
    currently surfaces as an unhandled IntegrityError, not a clean 400.
    """
    user = UserFactory(phone_number="+919876500013")
    mocker.patch.object(send_otp_sms_task, "delay")

    with pytest.raises(Exception):
        request_login_otp(str(user.phone_number))


# ---------- verify_login_otp ----------

def test_verify_login_otp_unknown_phone_raises_otp_invalid():
    with pytest.raises(OTPInvalidError):
        verify_login_otp(phone_number="+919999999998", code="123456")


def test_verify_login_otp_success_returns_tokens_and_marks_verified():
    user = UserFactory(phone_number="+919876500020")
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    _create_phone_otp_token(user, auth_method, raw_code="654321")

    result = verify_login_otp(phone_number=str(user.phone_number), code="654321")

    assert result["user"] == user
    assert result["access"]
    assert result["refresh"]
    user.refresh_from_db()
    assert user.last_login is not None


def test_verify_login_otp_wrong_code_raises_otp_invalid():
    user = UserFactory(phone_number="+919876500021")
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    _create_phone_otp_token(user, auth_method, raw_code="654321")

    with pytest.raises(OTPInvalidError):
        verify_login_otp(phone_number=str(user.phone_number), code="000000")


def test_verify_login_otp_expired_token_raises_otp_invalid():
    user = UserFactory(phone_number="+919876500022")
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    _create_phone_otp_token(user, auth_method, raw_code="654321", expired=True)

    with pytest.raises(OTPInvalidError):
        verify_login_otp(phone_number=str(user.phone_number), code="654321")


def test_verify_login_otp_locks_after_max_attempts():
    user = UserFactory(phone_number="+919876500023")
    auth_method = AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    _create_phone_otp_token(user, auth_method, raw_code="654321")

    for _ in range(phone_constants.OTP_MAX_ATTEMPTS):
        with pytest.raises(OTPInvalidError):
            verify_login_otp(phone_number=str(user.phone_number), code="000000")

    with pytest.raises(OTPLockedError):
        verify_login_otp(phone_number=str(user.phone_number), code="654321")