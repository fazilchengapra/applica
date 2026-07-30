from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from ...serializers.phone_serializers import RequestPhoneChangeSerializer
from app.apps.authentication.services.phone.request_phone_change import (
    request_phone_change,
)
from app.apps.authentication.exceptions.phone import (
    PhoneNumberInUseError,
    SamePhoneNumberError,
    PhoneChangeInvalidError,
    PhoneNotVerifiedError,
)
from app.apps.authentication.exceptions.otp import OTPCooldownError

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class RequestPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RequestPhoneChangeSerializer,
        responses={
            200: OpenApiResponse(
                description="Verification codes sent to both the current and new phone numbers.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "Verification codes sent to your current and new number."
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Same phone number, invalid change request, or current phone not verified.",
                examples=[
                    OpenApiExample(
                        "Same number",
                        value={
                            "detail": "New phone number must be different from your current one."
                        },
                    ),
                    OpenApiExample(
                        "Invalid change",
                        value={"detail": "Phone change request is invalid."},
                    ),
                    OpenApiExample(
                        "Not verified",
                        value={"detail": "Your current phone number is not verified."},
                    ),
                ],
            ),
            409: OpenApiResponse(
                description="New phone number is already in use by another account.",
                examples=[
                    OpenApiExample(
                        "Already in use",
                        value={"detail": "This phone number is already in use."},
                    )
                ],
            ),
            429: OpenApiResponse(
                description="Too many requests sent recently; cooldown in effect.",
                examples=[
                    OpenApiExample(
                        "Cooldown",
                        value={
                            "detail": "Please wait before requesting another change."
                        },
                    )
                ],
            ),
        },
        description=(
            "Starts the dual-confirmation phone change flow. Sends an OTP to both "
            "the user's current and new phone numbers; the change only completes "
            "once both sides confirm."
        ),
        summary="Request phone number change",
    )
    def post(self, request):
        serializer = RequestPhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_phone_change(
                request.user, str(serializer.validated_data["new_phone_number"])
            )
        except OTPCooldownError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except PhoneNumberInUseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except (
            SamePhoneNumberError,
            PhoneChangeInvalidError,
            PhoneNotVerifiedError,
        ) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Verification codes sent to your current and new number."},
            status=status.HTTP_200_OK,
        )
