from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.authentication.api.v1.exceptions import (
    AccountInactiveError,
    OTPInvalidError,
)
from app.apps.authentication.api.v1.services.phone.verify_otp import verify_phone_otp

User = get_user_model() 


def verify_login_otp(*, phone_number: str, code: str) -> dict:
    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        raise OTPInvalidError("Invalid phone number or code.")

    verify_phone_otp(user, code)  # raises OTPInvalidError / OTPLockedError on failure

    if not user.is_active:
        raise AccountInactiveError("This account has been deactivated.")

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": user}