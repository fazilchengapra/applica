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


class EmailChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=EmailChangeConfirmationSerializer,
        description="Confirm an email change using the token sent to the old or new email.",
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
