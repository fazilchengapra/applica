# user_mgmt/api/v1/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..serializers.me_serializer import MeSerializer
from ..serializers.dlt_account_serializer import DeleteAccountSerializer
from app.apps.users.services.me_service import get_current_user
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from app.apps.users.services.acc_dlt_service import delete_account
from app.apps.users.exception import InvalidPasswordError

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MeSerializer},
        description="Retrieves the authenticated user's own account details.",
        summary="Get current user",
    )
    def get(self, request):
        user = get_current_user(request.user.id)
        serializer = MeSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=DeleteAccountSerializer,
        responses={
            204: OpenApiResponse(
                description="Account deleted successfully. Auth cookies cleared."
            ),
            400: OpenApiResponse(
                description="Validation error, or incorrect password.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={
                            "detail": "Validation error",
                            "error": {"password": ["This field is required."]},
                        },
                    ),
                    OpenApiExample(
                        "Wrong password", value={"detail": "Password is incorrect."}
                    ),
                ],
            ),
        },
        description="Permanently deletes the authenticated user's account after confirming their password.",
        summary="Delete account",
    )
    def delete(self, request):
        serializer = DeleteAccountSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "Validation error", "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            delete_account(
                user=request.user,
                password=serializer.validated_data["password"],
            )
        except InvalidPasswordError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response
