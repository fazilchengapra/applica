from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from ...serializers.email_serializers import ResetPasswordSerializer
from app.apps.authentication.services.password.reset_password_service import reset_password
from app.apps.authentication.exceptions import TokenInvalidError


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

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
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Your password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
