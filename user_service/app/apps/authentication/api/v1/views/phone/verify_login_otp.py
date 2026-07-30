from ...serializers.phone_serializers import VerifyLoginOTPSerializer
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .....services.phone.verify_login_otp import verify_login_otp
from app.apps.authentication.exceptions.otp import OTPInvalidError, OTPLockedError
from app.apps.authentication.exceptions.account import AccountInactiveError
from rest_framework import status
from rest_framework.response import Response
from app.apps.authentication.utils import cookie

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample    

class VerifyLoginOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyLoginOTPSerializer,
        responses={
            200: OpenApiResponse(
                description="OTP verified. Login successful, auth cookies set on the response.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "user": {
                                "id": "b3b1e...uuid",
                                "phone_number": "+911234567890",
                            },
                            "message": "login success",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="OTP is invalid, or the account is inactive.",
                examples=[
                    OpenApiExample(
                        "Invalid OTP", value={"detail": "Invalid or expired code."}
                    ),
                    OpenApiExample(
                        "Account inactive",
                        value={"detail": "This account is inactive."},
                    ),
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
        description="Verifies a phone login OTP and logs the user in, setting HttpOnly access/refresh cookies.",
        summary="Verify login OTP",
    )
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
            {
                "user": {"id": user.id, "phone_number": str(user.phone_number)},
                "message": "login success",
            },
            status=status.HTTP_200_OK,
        )
        cookie.set_auth_cookies(
            response, access_token=result["access"], refresh_token=result["refresh"]
        )
        return response
