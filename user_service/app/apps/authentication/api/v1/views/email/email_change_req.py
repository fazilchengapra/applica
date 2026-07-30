from rest_framework.views import APIView
from rest_framework.response import Response

from ...serializers.email_serializers import EmailChangeReqSerializer
from rest_framework.permissions import IsAuthenticated

from app.apps.authentication.services.email.email_change_request import (
    request_email_change,
)

from app.apps.authentication.exceptions.email import (
    EmailInUseError,
    EmailChangeInvalidError,
    EmailNotVerifiedError,
    SameEmailError,
)
from app.apps.authentication.exceptions.token import TokenRequestCooldownError
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class EmailChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=EmailChangeReqSerializer,
        responses={
            200: OpenApiResponse(
                description="Verification codes sent to both the current and new email addresses.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"detail": "Verification codes sent to both your current and new email."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Request could not be processed.",
                examples=[
                    OpenApiExample("Email already in use", value={"detail": "This email is already in use."}),
                    OpenApiExample("Invalid change", value={"detail": "Email change request is invalid."}),
                    OpenApiExample("Current email not verified", value={"detail": "Your current email is not verified."}),
                    OpenApiExample("Same email", value={"detail": "New email must be different from your current email."}),
                ],
            ),
            429: OpenApiResponse(
                description="Too many requests sent recently; cooldown in effect.",
                examples=[
                    OpenApiExample("Cooldown", value={"detail": "Please wait before requesting another change."})
                ],
            ),
        },
        description=(
            "Starts the dual-confirmation email change flow. Sends a verification "
            "token to both the user's current and new email addresses; the change "
            "only completes once both sides confirm via EmailChangeConfirmView."
        ),
        summary="Request email change",
    )

    def post(self, request):
        serializer = EmailChangeReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_email_change(
                user=request.user,
                new_email=serializer.validated_data["new_email"],
            )
        except TokenRequestCooldownError as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except (
            EmailInUseError,
            EmailChangeInvalidError,
            EmailNotVerifiedError,
            SameEmailError,
        ) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": "Verification codes sent to both your current and new email."},
            status=status.HTTP_200_OK,
        )