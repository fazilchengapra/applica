from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.apps.profiles.api.v1.serializer import ProfileSerializer
from app.apps.profiles.exceptions import ProfileNotFound
from app.apps.profiles.services.get_profile_service import get_profile

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class GetProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: ProfileSerializer,
            404: OpenApiResponse(
                description="Profile not found for the authenticated user.",
                examples=[
                    OpenApiExample("Not found", value={"detail": "Profile not found."})
                ],
            ),
        },
        description="Retrieves the authenticated user's profile.",
        summary="Get profile",
    )
    def get(self, request):
        try:
            profile = get_profile(request.user.id)
        except ProfileNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
