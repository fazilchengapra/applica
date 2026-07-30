from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response

from app.apps.authentication.services.phone.request_login_otp import request_login_otp

from app.apps.authentication.exceptions.otp import OTPCooldownError
from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.phone import PhoneNotVerifiedError

from ...serializers.phone_serializers import RequestLoginOTPSerializer

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class RequestLoginOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RequestLoginOTPSerializer,
        responses={
            200: OpenApiResponse(
                description="Generic success message, returned even if the number isn't registered.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "If this number is registered, a code has been sent."
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Number not registered, or the phone is not yet verified.",
                examples=[
                    OpenApiExample("Not found", value={"detail": "User not found."}),
                    OpenApiExample(
                        "Not verified",
                        value={"detail": "Phone number is not verified."},
                    ),
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
        description="Sends a login OTP to the given phone number, if registered and verified.",
        summary="Request login OTP",
    )
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
