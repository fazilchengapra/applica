from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from app.apps.authentication.services.password.change_pass_service import (
    change_password,
)
from ...serializers.email_serializers import ChangePasswordSerializer
from app.apps.authentication.exceptions import ConfirmPasswordNotMatchError


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            serializer = ChangePasswordSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(
                    {"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

            change_password(
                user=request.user,
                old_password=serializer.validated_data["old_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ConfirmPasswordNotMatchError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Your password has been changed successfully."},
            status=status.HTTP_200_OK,
        )
