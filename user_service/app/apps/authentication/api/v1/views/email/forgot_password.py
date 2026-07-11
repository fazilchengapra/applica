from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .....services.email.forgot_password_service import request_reset
from ...serializers.email_serializers import ForgotPasswordRequestSerializer

from .....exceptions import UserNotFoundError


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_reset(serializer.validated_data["email"])
        except UserNotFoundError as exc:
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
