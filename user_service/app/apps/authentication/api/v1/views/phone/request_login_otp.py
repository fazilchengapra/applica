from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response

from app.apps.authentication.services.phone.request_login_otp import request_login_otp

from app.apps.authentication.exceptions.otp import OTPCooldownError
from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.phone import PhoneNotVerifiedError

from ...serializers.phone_serializers import RequestLoginOTPSerializer


class RequestLoginOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestLoginOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_login_otp(serializer.validated_data["phone_number"])
        except (OTPCooldownError, UserNotFoundError, PhoneNotVerifiedError) as exc:
            # only cooldownerror have a different status code
            status_code = (
                status.HTTP_429_TOO_MANY_REQUESTS
                if isinstance(exc, OTPCooldownError)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=status_code)

        return Response(
            {"message": "If this number is registered, a code has been sent."},
            status=status.HTTP_200_OK,
        )
