from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .....services.phone.verify_phone_change import verify_phone_change

from ...serializers.phone_serializers import VerifyPhoneChangeSerializer

from app.apps.authentication.exceptions.otp import OTPLockedError
from app.apps.authentication.exceptions.phone import PhoneChangeInvalidError

class VerifyPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verify_phone_change(
                request.user,
                old_code=serializer.validated_data["old_code"],
                new_code=serializer.validated_data["new_code"],
            )
        except OTPLockedError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except PhoneChangeInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Phone number updated."}, status=status.HTTP_200_OK)
