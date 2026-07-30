from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from rest_framework.permissions import AllowAny

from ..serializers.register_serializer import RegisterSerializer
from app.apps.users.services.register_service import register_user

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class UserView(APIView):
    # API view for user creation.

    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="User registered successfully. Verification link sent to email.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "user created success!",
                            "data": {
                                "id": "b3b1e...uuid",
                                "email": "user@example.com",
                                "phone_number": "+911234567890",
                            },
                            "detail": "Verification Link Sended to Your Email",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error in submitted registration data.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={
                            "message": "Data validation error",
                            "errors": {"email": ["This field is required."]},
                        },
                    )
                ],
            ),
            409: OpenApiResponse(
                description="A user with this email or phone number already exists.",
                examples=[
                    OpenApiExample(
                        "Duplicate user",
                        value={
                            "detail": "A user with this email or phone number already exists."
                        },
                    )
                ],
            ),
        },
        description="Registers a new user account and sends an email verification link.",
        summary="Register user",
    )
    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        # validating the giving data
        if not serializer.is_valid():
            return Response(
                {"message": "Data validation error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = register_user(**serializer.validated_data)

        except IntegrityError:
            return Response(
                {"detail": "A user with this email or phone number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "message": "user created success!",
                "data": {
                    "id": user.id,
                    "email": user.email,
                    "phone_number": str(user.phone_number),
                },
                "detail": "Verification Link Sended to Your Email",
            },
            status=status.HTTP_201_CREATED,
        )
