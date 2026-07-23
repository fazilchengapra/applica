from django.db import transaction

from .exchange_code_service import exchange_code
from .verify_google_token_service import verify_google_id_token

from app.apps.authentication.models import AuthMethod
from app.apps.users.models import User
from app.apps.profiles.models import Profile

from rest_framework_simplejwt.tokens import RefreshToken

from app.apps.authentication.exceptions.account import AccountInActiveError


@transaction.atomic
def authenticate_with_google(code: str) -> User:

    # get a token using the user givin code
    tokens = exchange_code(code)

    # get google token_id_response using the id_token like -> email, name, and sub
    claims = verify_google_id_token(tokens["id_token"])

    # filtering the auth method is already exist
    auth_method = (
        AuthMethod.objects.filter(provider="google", provider_uid=claims["sub"])
        .select_related("user")
        .first()
    )

    # check the user exist
    user = User.objects.filter(email=claims["email"]).first()

    # checking the user is active or not
    if user and not user.is_active:
        # rise a error for inactive accounts
        raise AccountInActiveError("This account is banned please contact our support")

    # creating a record for new user registration
    if not user:
        user = User.objects.create(
            email=claims["email"], is_email_verified=claims["email_verified"]
        )
        profile = Profile.objects.create(
            user=user,
            first_name=claims["name"],
            display_name=claims["given_name"],
            avatar_url=claims["picture"],
        )

    # create a auth method that not exist a user account
    if not auth_method:

        AuthMethod.objects.create(
            user=user,
            provider=AuthMethod.GOOGLE,
            provider_uid=claims["sub"],
            is_verified=True,
        )

    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": user,
    }
