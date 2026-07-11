from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .....services.phone.request_otp import request_phone_otp
from .....exceptions import OTPCooldownError, PhoneAlreadyVerifiedError
from rest_framework.response import Response
from rest_framework import status


class RequestPhoneOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request_phone_otp(request.user)
        except OTPCooldownError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except PhoneAlreadyVerifiedError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Verification code sent."}, status=status.HTTP_200_OK
        )