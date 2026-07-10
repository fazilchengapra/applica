from ...serializers.phone_related_serializer import VerifyLoginOTPSerializer
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from ...services.phone.verify_login_otp import verify_login_otp
from ...exceptions import OTPInvalidError, OTPLockedError, AccountInactiveError
from rest_framework import status
from rest_framework.response import Response
from app.apps.authentication.utils import cookie

class VerifyLoginOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyLoginOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = verify_login_otp(
                phone_number=serializer.validated_data["phone_number"],
                code=serializer.validated_data["code"],
            )
        except OTPLockedError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except (OTPInvalidError, AccountInactiveError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        user = result["user"]
        response = Response(
            {"user": {"id": user.id, "phone_number": str(user.phone_number)}},
            status=status.HTTP_200_OK,
        )
        cookie.set_auth_cookies(
            response, access_token=result["access"], refresh_token=result["refresh"]
        )
        return response
