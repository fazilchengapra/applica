from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiResponse, extend_schema

from app.apps.profiles.api.v1.admin_profile_serializer import (
    AdminProfileOverviewSerializer,
)
from app.apps.profiles.exceptions import ProfileNotFound
from app.apps.profiles.services.get_profile_service import get_profile


class AdminProfileView(APIView):
    @extend_schema(
        responses={
            200: AdminProfileOverviewSerializer,
            404: OpenApiResponse(description="Profile not found."),
        },
        description="Retrieves a user's profile for admin viewing.",
        summary="View user profile",
    )
    def get(self, request, user_id):
        try:
            profile = get_profile(user_id)
        except ProfileNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminProfileOverviewSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
