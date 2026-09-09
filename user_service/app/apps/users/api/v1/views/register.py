from django.contrib.auth import get_user_model
from django.db import IntegrityError, models
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers.register_serializer import RegisterSerializer
from ..serializers.users_admin_serializers import UserListSerializer
from ..serializers.users_admin_serializers import UserActiveSerializer
from app.apps.users.services.register_service import register_user

# pagination
from ..pagination import UserListPagination

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from app.apps.users.models import User


class UserView(APIView):

    @extend_schema(
        summary="List users",
        description="Returns a paginated list of users for table display.",
        responses={200: UserListSerializer(many=True)},
    )
    def get(self, request):
        search = (request.query_params.get("search") or "").strip()
        users = User.objects.only("id", "email", "is_active").order_by("id")

        if search:
            search_value = str(search).lower()
            username_value = search_value.split("@", 1)[0]
            q = models.Q(email__icontains=search_value) | models.Q(
                email__icontains=username_value
            )

            try:
                q |= models.Q(id=int(search_value))
            except ValueError:
                pass

            users = users.filter(q)

        paginator = UserListPagination()
        page = paginator.paginate_queryset(users, request)

        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class AdminUserToggleView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Toggle user active status",
        description="Enable or disable a user account using the is_active flag. Authorization is enforced by Kong before this request reaches the service.",
        request={
            "type": "object",
            "properties": {"is_active": {"type": "boolean"}},
            "required": ["is_active"],
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "is_active": {"type": "boolean"},
                },
            }
        },
    )
    def patch(self, request, user_id=None):
        try:
            user = User.objects.get(pk=user_id)
            print(request.data)
            serializer = UserActiveSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"id": user.id, "is_active": user.is_active},
            status=status.HTTP_200_OK,
        )

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
