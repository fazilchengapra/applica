from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from app.apps.authentication.services.oauth.auth_with_google_service import (
    authenticate_with_google,
)
from app.apps.authentication.utils import cookie
from app.apps.authentication.exceptions.account import AccountInActiveError


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"detail": "code is required"}, status=400)

        try:
            res = authenticate_with_google(code)

        except AccountInActiveError as e:
            return Response({"detail": e}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as ex:
            return Response(
                {"detail": "Google authentication failed"},
                status=status.HTTP_400_BAD_REQUEST,
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
