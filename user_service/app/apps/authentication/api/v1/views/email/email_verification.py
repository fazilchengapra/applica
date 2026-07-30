from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...serializers.email_serializers import VerifyEmailSerializer

from .....services.email.email_verify import verify_email

# exception
from app.apps.authentication.exceptions.email import EmailVerificationInvalidError

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class VerifyEmailView(APIView):

    @extend_schema(
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(
                description="Email verified successfully.",
                examples=[
                    OpenApiExample(
                        "Success", value={"message": "Email verification success"}
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error, or token is invalid/expired.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={
                            "detail": "validation error",
                            "error": {"token": ["This field is required."]},
                        },
                    ),
                    OpenApiExample(
                        "Invalid token",
                        value={"detail": "Verification token is invalid or expired."},
                    ),
                ],
            ),
        },
        description="Confirms email ownership using the token sent to the user's email address.",
        summary="Verify email",
    )   
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "validation error", "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verify_email(
                raw_token=serializer.validated_data["token"],
            )

        except EmailVerificationInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Email verification success"}, status=status.HTTP_200_OK
        )
