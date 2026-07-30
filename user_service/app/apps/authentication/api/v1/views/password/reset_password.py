from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from ...serializers.email_serializers import ResetPasswordSerializer
from app.apps.authentication.services.password.reset_password_service import (
    reset_password,
)
from app.apps.authentication.exceptions.token import (
    TokenInvalidError,
    TokenExpiredError,
)

# swagger api docs
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"message": "Your password has been reset successfully."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Token is invalid or expired, or the new password fails validation.",
                examples=[
                    OpenApiExample(
                        "Invalid token", value={"detail": "Token is invalid."}
                    ),
                    OpenApiExample(
                        "Expired token", value={"detail": "Token has expired."}
                    ),
                    OpenApiExample(
                        "Weak password",
                        value={"detail": "Password does not meet requirements."},
                    ),
                ],
            ),
        },
        description="Resets a user's password using the token sent via the forgot-password flow.",
        summary="Reset password",
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reset_password(
                raw_token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except TokenInvalidError as ex:
            return Response({"detail": str(ex)}, status=status.HTTP_400_BAD_REQUEST)

        except TokenExpiredError as ex:
            return Response({"detail": str(ex)}, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Your password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
