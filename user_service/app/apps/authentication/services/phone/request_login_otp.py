from django.contrib.auth import get_user_model

from ...exceptions import UserNotFoundError
from app.apps.authentication.services.phone.request_otp import request_phone_otp

User = get_user_model()


def request_login_otp(phone_number: str) -> None:
    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:

        raise UserNotFoundError("User not exist!")

    request_phone_otp(user, login=True)
