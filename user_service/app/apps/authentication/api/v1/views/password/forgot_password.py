from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .....services.password.forgot_password_service import request_reset
from ...serializers.email_serializers import CommonEmailSerializer

from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.email import EmailNotVerifiedError

# swagger api docs
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CommonEmailSerializer,
        responses={
            200: OpenApiResponse(
                description="Generic success message, returned even if the email doesn't correspond to an account.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "If an account with that email exists, a reset link has been sent."
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Account not found, or the associated email is not verified.",
                examples=[
                    OpenApiExample("Not found", value={"detail": "User not found."}),
                    OpenApiExample(
                        "Not verified", value={"detail": "Email is not verified."}
                    ),
                ],
            ),
        },
        description="Requests a password reset link for the given email address.",
        summary="Forgot password",
    )
    def post(self, request):
        serializer = CommonEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_reset(serializer.validated_data["email"])
        except (UserNotFoundError, EmailNotVerifiedError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # generic response regardless of whether the email exists
        return Response(
            {
                "message": "If an account with that email exists, a reset link has been sent."
            },
            status=status.HTTP_200_OK,
        )
