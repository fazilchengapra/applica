from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.apps.profiles.api.v1.serializer import ProfileSerializer
from app.apps.profiles.exceptions import ProfileNotFound
from app.apps.profiles.services.update_profile_service import update_profile


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            res = update_profile(request.user.id, request.data)
        except ProfileNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileSerializer(res)
        return Response(serializer.data, status=status.HTTP_200_OK)
