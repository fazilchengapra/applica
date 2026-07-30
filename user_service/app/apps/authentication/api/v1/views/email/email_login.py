from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...serializers.email_serializers import EmailLoginSerializer

from app.apps.authentication.services.email.login import login_user

from app.apps.authentication.exceptions.account import AccountInactiveError

from app.apps.authentication.exceptions.authentication import InvalidCredentialsError
from app.apps.authentication.exceptions.email import EmailInActiveError

from app.apps.authentication.utils import cookie

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class EmailLoginView(APIView):
    @extend_schema(
        request=EmailLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful. Auth cookies are set on the response.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "access": "<jwt>",
                            "refresh": "<jwt>",
                            "user": {
                                "id": "b3b1e...uuid",
                                "email": "user@example.com",
                                "phone_number": "+911234567890",
                                "is_email_verified": True,
                                "is_phone_verified": False,
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error or invalid credentials.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={
                            "detail": "Validation error ",
                            "error": {"email": ["This field is required."]},
                        },
                    ),
                    OpenApiExample(
                        "Invalid credentials",
                        value={"detail": "Invalid email or password."},
                    ),
                ],
            ),
            403: OpenApiResponse(
                description="Account or email is inactive.",
                examples=[
                    OpenApiExample(
                        "Account inactive",
                        value={"detail": "This account is inactive."},
                    ),
                    OpenApiExample(
                        "Email inactive", value={"detail": "This email is inactive."}
                    ),
                ],
            ),
        },
        description="Authenticates a user via email/password and sets HttpOnly access/refresh cookies on success.",
        summary="Login with email",
    )
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "Validation error ", "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            res = login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                request=request,
            )

        except AccountInactiveError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except InvalidCredentialsError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EmailInActiveError as ex:
            return Response(
                {"detail": str(ex)},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = res["user"]

        response = Response(
            {
                "access": res["access"],
                "refresh": res["refresh"],
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "phone_number": str(user.phone_number),
                    "is_email_verified": user.is_email_verified,
                    "is_phone_verified": user.is_phone_verified,
                },
            },
            status=status.HTTP_200_OK,
        )

        cookie.set_auth_cookies(
            response, access_token=res["access"], refresh_token=res["refresh"]
        )

        return response
