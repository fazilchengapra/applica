import pytest
from django.core.cache import cache

from app.apps.authentication.exceptions.otp import OTPCooldownError, OTPLockedError
from app.apps.authentication.exceptions.phone import (
    PhoneNumberInUseError,
    PhoneChangeInvalidError,
    PhoneNotVerifiedError,
    SamePhoneNumberError,
)
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.constants import verification_type
from app.apps.authentication.services.phone.request_phone_change import request_phone_change
from app.apps.authentication.services.phone.verify_phone_change import verify_phone_change
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


# ---------- request_phone_change ----------

def test_request_phone_change_number_already_in_use_raises():
    UserFactory(phone_number="+919876500100")
    user = UserFactory(phone_number="+919876500101")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)

    with pytest.raises(PhoneNumberInUseError):
        request_phone_change(user, "+919876500100")


def test_request_phone_change_no_auth_method_raises_invalid():
    user = UserFactory(phone_number="+919876500102")

    with pytest.raises(PhoneChangeInvalidError):
        request_phone_change(user, "+919876500199")


def test_request_phone_change_unverified_auth_method_raises_not_verified():
    user = UserFactory(phone_number="+919876500103")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=False)

    with pytest.raises(PhoneNotVerifiedError):
        request_phone_change(user, "+919876500198")


def test_request_phone_change_same_number_raises():
    user = UserFactory(phone_number="+919876500104")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)

    with pytest.raises(SamePhoneNumberError):
        request_phone_change(user, "+919876500104")


def test_request_phone_change_success_creates_both_tokens_and_sends_both_sms(mocker):
    user = UserFactory(phone_number="+919876500105")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    mock_delay = mocker.patch.object(send_otp_sms_task, "delay")

    request_phone_change(user, "+919876500197")

    assert VerificationToken.objects.filter(
        user=user, type=verification_type.PHONE_CHANGE_OLD_TYPE, used_at__isnull=True
    ).exists()
    assert VerificationToken.objects.filter(
        user=user, type=verification_type.PHONE_CHANGE_NEW_TYPE, used_at__isnull=True
    ).exists()
    assert mock_delay.call_count == 2


def test_request_phone_change_respects_cooldown(mocker):
    user = UserFactory(phone_number="+919876500106")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    mocker.patch.object(send_otp_sms_task, "delay")

    request_phone_change(user, "+919876500196")

    with pytest.raises(OTPCooldownError):
        request_phone_change(user, "+919876500195")


# ---------- verify_phone_change ----------

def _start_phone_change(user, new_number="+919876500200", mocker=None):
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    request_phone_change(user, new_number)
    old = VerificationToken.objects.get(user=user, type=verification_type.PHONE_CHANGE_OLD_TYPE)
    new = VerificationToken.objects.get(user=user, type=verification_type.PHONE_CHANGE_NEW_TYPE)
    return old, new


def test_verify_phone_change_no_pending_request_raises():
    user = UserFactory(phone_number="+919876500107")

    with pytest.raises(PhoneChangeInvalidError):
        verify_phone_change(user, old_code="123456", new_code="654321")


def test_verify_phone_change_wrong_codes_raises_and_increments_attempts(mocker):
    user = UserFactory(phone_number="+919876500108")
    mocker.patch.object(send_otp_sms_task, "delay")
    _start_phone_change(user, "+919876500201")

    with pytest.raises(PhoneChangeInvalidError):
        verify_phone_change(user, old_code="000000", new_code="000000")


def test_verify_phone_change_success_updates_phone_number(mocker):
    user = UserFactory(phone_number="+919876500109")
    mocker.patch.object(send_otp_sms_task, "delay")
    old, new = _start_phone_change(user, "+919876500202")

    raw_old = "111111"
    raw_new = "222222"
    old.token_hash = token_utils.hash_token(raw_old)
    old.save(update_fields=["token_hash"])
    new.token_hash = token_utils.hash_token(raw_new)
    new.save(update_fields=["token_hash"])

    verify_phone_change(user, old_code=raw_old, new_code=raw_new)

    user.refresh_from_db()
    assert str(user.phone_number) == "+919876500202"
    assert user.is_phone_verified is True


def test_verify_phone_change_locks_after_max_attempts(mocker):
    from app.apps.authentication.constants import phone as phone_constants

    user = UserFactory(phone_number="+919876500110")
    mocker.patch.object(send_otp_sms_task, "delay")
    _start_phone_change(user, "+919876500203")

    for _ in range(phone_constants.OTP_MAX_ATTEMPTS):
        with pytest.raises(PhoneChangeInvalidError):
            verify_phone_change(user, old_code="000000", new_code="000000")

    with pytest.raises(OTPLockedError):
        verify_phone_change(user, old_code="000000", new_code="000000")