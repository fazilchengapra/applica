from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .....services.phone.verify_phone_change import verify_phone_change

from ...serializers.phone_serializers import VerifyPhoneChangeSerializer

from app.apps.authentication.exceptions.otp import OTPLockedError
from app.apps.authentication.exceptions.phone import PhoneChangeInvalidError

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class VerifyPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=VerifyPhoneChangeSerializer,
        responses={
            200: OpenApiResponse(
                description="Phone number updated successfully.",
                examples=[
                    OpenApiExample(
                        "Success", value={"message": "Phone number updated."}
                    )
                ],
            ),
            400: OpenApiResponse(
                description="One or both OTP codes are invalid or expired.",
                examples=[
                    OpenApiExample(
                        "Invalid codes",
                        value={"detail": "One or both codes are invalid or expired."},
                    )
                ],
            ),
            429: OpenApiResponse(
                description="Too many failed attempts; OTP is locked.",
                examples=[
                    OpenApiExample(
                        "Locked",
                        value={
                            "detail": "Too many failed attempts. Please request a new code."
                        },
                    )
                ],
            ),
        },
        description=(
            "Confirms a phone number change by verifying the OTP codes sent to "
            "both the current and new phone numbers."
        ),
        summary="Verify phone number change",
    )
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
