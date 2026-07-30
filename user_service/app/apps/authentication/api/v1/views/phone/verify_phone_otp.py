from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ...serializers.phone_serializers import VerifyPhoneOTPSerializer
from app.apps.authentication.services.phone.verify_otp import verify_phone_otp

from app.apps.authentication.exceptions.otp import OTPLockedError, OTPInvalidError

# api docs
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class VerifyPhoneOTPView(APIView):  
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=VerifyPhoneOTPSerializer,
        responses={
            200: OpenApiResponse(
                description="Phone number verified successfully.",
                examples=[
                    OpenApiExample(
                        "Success", value={"message": "Phone number verified."}
                    )
                ],
            ),
            400: OpenApiResponse(
                description="OTP code is invalid or expired.",
                examples=[
                    OpenApiExample(
                        "Invalid OTP", value={"detail": "Invalid or expired code."}
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
        description="Verifies the authenticated user's phone number using an OTP code.",
        summary="Verify phone number",
    )
    def post(self, request):
        serializer = VerifyPhoneOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verify_phone_otp(request.user, serializer.validated_data["code"])
        except OTPLockedError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except OTPInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Phone number verified."}, status=status.HTTP_200_OK
        )
