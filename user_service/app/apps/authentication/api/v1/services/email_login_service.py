from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from ..exceptions.login_exceptions import AccountInactiveError, InvalidCredentialsError, EmailInActiveError
from app.apps.authentication.models import AuthMethod
from app.apps.authentication.constants import verification_type


def login_user(*, email: str, password: str, request=None) -> dict:
    email = email.lower().strip()

    user = authenticate(request=request, email=email, password=password)

    auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.EMAIL, is_verified=True, is_active=True
    ).first()

    if not auth_method:
        raise EmailInActiveError("Please verify your email")

    if user is None:
        raise InvalidCredentialsError("Invalid email or password.")

    if not user.is_active:
        raise AccountInactiveError("This account has been deactivated.")

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    AuthMethod.objects.filter(user=user, provider=verification_type.EMAIL_TYPE).update(
        last_used_at=timezone.now()
    )

    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": user,
    }
