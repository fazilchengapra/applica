from rest_framework.views import APIView
from rest_framework.response import Response

from ...serializers.token_serializers import EmailChangeConfirmationSerializer
from rest_framework.permissions import IsAuthenticated

from app.apps.authentication.exceptions.email import (
    EmailInUseError,
)
from rest_framework import status
from app.apps.authentication.exceptions.email import (
    EmailChangeTokenInvalidError,
    EmailInUseError,
)
from app.apps.authentication.services.email.email_change_confirm import (
    confirm_email_change,
)

from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiResponse, OpenApiExample
from app.apps.authentication.openapi import COMMON_AUTH_ERROR_RESPONSES


class EmailChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EmailChangeConfirmationSerializer,
        responses={
            200: OpenApiResponse(
                description="Confirmation accepted. May be fully complete or still awaiting the other side.",
                examples=[
                    OpenApiExample(
                        "Fully completed",
                        value={
                            "detail": "Email updated successfully.",
                            "completed": True,
                        },
                    ),
                    OpenApiExample(
                        "Awaiting other confirmation",
                        value={
                            "detail": "Confirmed. Waiting for the other email to confirm.",
                            "completed": False,
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Token is invalid/expired, or the new email is already in use.",
                examples=[
                    OpenApiExample(
                        "Invalid token",
                        value={"detail": "Token is invalid or expired."},
                    ),
                    OpenApiExample(
                        "Email in use", value={"detail": "Email is already in use."}
                    ),
                ],
            ),
        },
        description=(
            "Confirms one side of the dual-confirmation email change flow. "
            "Both the old and new email addresses must independently confirm "
            "via their own token before the change is finalized."
        ),
        summary="Confirm email change",
    )
    def post(self, request):
        serializer = EmailChangeConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            is_complete = confirm_email_change(
                user=request.user,
                raw_token=serializer.validated_data["token"],
            )
        except (EmailChangeTokenInvalidError, EmailInUseError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if is_complete:
            return Response(
                {"detail": "Email updated successfully.", "completed": True},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": "Confirmed. Waiting for the other email to confirm.",
                "completed": False,
            },
            status=status.HTTP_200_OK,
        )
