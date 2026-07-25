import pytest
from django.core.cache import cache

from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.services.phone.request_otp import request_phone_otp
from app.apps.authentication.tests.factories import AuthMethodFactory
from app.apps.users.tests.factories import UserFactory

from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.authentication.constants import verification_type
from app.apps.authentication.utils.cooldown import get_cool_down
from app.apps.authentication.constants import cooldown

from app.apps.authentication.exceptions.phone import PhoneAlreadyVerifiedError

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_request_phone_otp_initial_verification(mocker):

    user = UserFactory(phone_number="+919876500300")
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=False)
    mocker.patch("app.apps.authentication.services.phone.request_otp.send_otp_sms_task.delay")
    request_phone_otp(user, login=False)

    assert VerificationToken.objects.filter(user=user, type=verification_type.PHONE_TYPE).count() == 1
    assert cache.get(get_cool_down(cooldown.OTP_COOLDOWN, user.id)) is True

def test_request_phone_otp_after_verified_phone(mocker):

    user = UserFactory(phone_number="+919876500300", is_phone_verified=True)
    AuthMethodFactory(user=user, provider=AuthMethod.MOBILE, is_verified=True)
    mocker.patch("app.apps.authentication.services.phone.request_otp.send_otp_sms_task.delay")
    with pytest.raises(PhoneAlreadyVerifiedError):
        request_phone_otp(user, login=False)