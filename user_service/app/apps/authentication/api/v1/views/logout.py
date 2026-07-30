from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.response import Response
from rest_framework import status

from app.apps.authentication.utils import cookie

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                description="Logged out successfully. Refresh token blacklisted (if valid) and auth cookies cleared.",
                examples=[OpenApiExample("Success", value={"message": "Logged out."})],
            ),
        },
        description=(
            "Logs out the authenticated user. Blacklists the refresh token if present "
            "and valid, then clears the access/refresh HttpOnly cookies. Always returns "
            "200 even if the refresh token was already expired or missing."
        ),
        summary="Logout",
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass  # already invalid/expired — nothing to blacklist

        response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
        cookie.clear_auth_cookies(response)
        return response
