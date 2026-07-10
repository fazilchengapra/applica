from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ...serializers.verify_phone_otp_serializer import VerifyPhoneOTPSerializer
from ...services.phone.verify_otp import verify_phone_otp

from ...exceptions import OTPLockedError, OTPInvalidError

class VerifyPhoneOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPhoneOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verify_phone_otp(request.user, serializer.validated_data["code"])
        except OTPLockedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except OTPInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Phone number verified."}, status=status.HTTP_200_OK)