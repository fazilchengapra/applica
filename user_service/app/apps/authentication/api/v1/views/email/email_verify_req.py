from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from app.apps.authentication.services.email.email_verify_req import request_verification
from ...serializers.email_serializers import CommonEmailSerializer

from app.apps.authentication.exceptions.account import UserNotFoundError
from app.apps.authentication.exceptions.email import EmailAlreadyVerifiedError
from app.apps.authentication.exceptions.token import TokenRequestCooldownError
from app.apps.common.exceptions import UnexpectedError

# swagger
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from app.apps.authentication.openapi import COMMON_AUTH_ERROR_RESPONSES


class RequestEmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CommonEmailSerializer,
        responses={
            200: OpenApiResponse(
                description="Verification email sent successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "Verification email sent. Please check your inbox."
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error, or email is already verified.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={"details": {"email": ["This field is required."]}},
                    ),
                    OpenApiExample(
                        "Already verified",
                        value={"detail": "Email is already verified."},
                    ),
                ],
            ),
            **COMMON_AUTH_ERROR_RESPONSES,
        },
        description="Requests a verification email for the given address.",
        summary="Request email verification",
    )
    def post(self, request):
        try:
            serializer = CommonEmailSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(
                    {"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )
            request_verification(serializer.validated_data["email"])
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except UserNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        except EmailAlreadyVerifiedError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except TokenRequestCooldownError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        except UnexpectedError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "Verification email sent. Please check your inbox."},
            status=status.HTTP_200_OK,
        )
