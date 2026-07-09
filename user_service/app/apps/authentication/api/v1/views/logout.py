from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.response import Response
from rest_framework import status

from ..utils import clear_auth_cookies


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass  # already invalid/expired — nothing to blacklist

        response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response