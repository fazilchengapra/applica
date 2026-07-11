from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...serializers.email_serializers import EmailLoginSerializer

from app.apps.authentication.services.email.login import login_user

from app.apps.authentication.exceptions.account import (
    AccountInactiveError,
    UserNotFoundError,
)

from app.apps.authentication.exceptions.authentication import InvalidCredentialsError
from app.apps.authentication.exceptions.email import EmailInActiveError

from app.apps.authentication.utils import cookie

class EmailLoginView(APIView):
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "Validation error ", "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            res = login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                request=request,
            )
        except UserNotFoundError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AccountInactiveError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except InvalidCredentialsError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except EmailInActiveError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = res["user"]

        response = Response(
            {
                "access": res["access"],
                "refresh": res["refresh"],
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "phone_number": str(user.phone_number),
                    "is_email_verified": user.is_email_verified,
                    "is_phone_verified": user.is_phone_verified,
                },
            },
            status=status.HTTP_200_OK,
        )

        cookie.set_auth_cookies(
            response, access_token=res["access"], refresh_token=res["refresh"]
        )

        return response
