from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from ...serializers.phone_serializers import RequestPhoneChangeSerializer
from app.apps.authentication.services.phone.request_phone_change import (
    request_phone_change,
)
from app.apps.authentication.exceptions.phone import (
    PhoneNumberInUseError,
    SamePhoneNumberError,
)
from app.apps.authentication.exceptions.otp import OTPCooldownError

class RequestPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RequestPhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_phone_change(
                request.user, str(serializer.validated_data["new_phone_number"])
            )
        except OTPCooldownError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except PhoneNumberInUseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except SamePhoneNumberError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Verification codes sent to your current and new number."},
            status=status.HTTP_200_OK,
        )
