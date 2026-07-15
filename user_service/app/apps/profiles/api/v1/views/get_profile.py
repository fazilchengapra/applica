from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.apps.profiles.api.v1.serializer import ProfileSerializer
from app.apps.profiles.exceptions import ProfileNotFound
from app.apps.profiles.services.get_profile_service import get_profile


class GetProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_profile(request.user.id)
        except ProfileNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
