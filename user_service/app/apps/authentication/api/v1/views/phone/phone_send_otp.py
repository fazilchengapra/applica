from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from app.apps.authentication.services.phone.request_otp import request_phone_otp
from app.apps.authentication.exceptions.otp import OTPCooldownError
from app.apps.authentication.exceptions.phone import PhoneAlreadyVerifiedError

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class RequestPhoneOTPView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                description="OTP sent to the user's phone number.",
                examples=[
                    OpenApiExample(
                        "Success", value={"message": "Verification code sent."}
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Phone number is already verified.",
                examples=[
                    OpenApiExample(
                        "Already verified",
                        value={"detail": "Phone number is already verified."},
                    )
                ],
            ),
            429: OpenApiResponse(
                description="Too many OTP requests recently; cooldown in effect.",
                examples=[
                    OpenApiExample(
                        "Cooldown",
                        value={"detail": "Please wait before requesting another code."},
                    )
                ],
            ),
        },
        description="Sends an OTP to the authenticated user's registered phone number for verification.",
        summary="Request phone verification OTP",
    )
    def post(self, request):
        try:
            request_phone_otp(request.user)
        except OTPCooldownError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except PhoneAlreadyVerifiedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Verification code sent."}, status=status.HTTP_200_OK
        )
