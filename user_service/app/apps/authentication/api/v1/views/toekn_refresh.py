from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

from app.apps.authentication.utils import cookie

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                description="Access token refreshed successfully. New access cookie set on the response.",
                examples=[
                    OpenApiExample("Success", value={"message": "Token refreshed."})
                ],
            ),
            401: OpenApiResponse(
                description="Refresh token cookie is missing, invalid, or expired.",
                examples=[
                    OpenApiExample(
                        "Missing token", value={"detail": "Refresh token missing."}
                    ),
                    OpenApiExample(
                        "Invalid/expired token",
                        value={"detail": "Invalid or expired refresh token."},
                    ),
                ],
            ),
        },
        description=(
            "Issues a new access token using the refresh token stored in the HttpOnly "
            "cookie. Reads the refresh token from the cookie, not the request body."
        ),
        summary="Refresh access token",
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE)
        if raw_refresh is None:
            return Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = str(refresh.access_token)

        response = Response({"message": "Token refreshed."}, status=status.HTTP_200_OK)
        cookie.set_access_cookie(response, access_token=access_token)
        return response
