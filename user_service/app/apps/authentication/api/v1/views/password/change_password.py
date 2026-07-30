from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from app.apps.authentication.services.password.change_pass_service import (
    change_password,
)
from ...serializers.email_serializers import ChangePasswordSerializer
from app.apps.authentication.exceptions.password import ConfirmPasswordNotMatchError

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password changed successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "Your password has been changed successfully."
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error, new/confirm password mismatch, or incorrect old password.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={"detail": {"new_password": ["This field is required."]}},
                    ),
                    OpenApiExample(
                        "Confirm mismatch",
                        value={
                            "detail": "New password and confirm password do not match."
                        },
                    ),
                    OpenApiExample(
                        "Wrong old password",
                        value={"detail": "Old password is incorrect."},
                    ),
                ],
            ),
        },
        description="Changes the authenticated user's password. Requires the correct old password and a matching new/confirm pair.",
        summary="Change password",
    )
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
