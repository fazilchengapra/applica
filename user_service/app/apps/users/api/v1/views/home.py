"""Internal home-account aggregate consumed by the BFF in ai_service.

Not a public endpoint. It is reachable only with the shared internal secret and
exists so the BFF can assemble ``GET /api/ai/v1/home`` from a single call rather
than fanning out to several upstreams. The public, user-facing home endpoint
lives in ai_service.
"""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.apps.common.permissions import InternalSecretPermission
from app.apps.users.api.v1.serializers.home_serializer import HomeAccountSerializer
from app.apps.users.services.home_service import UserNotFoundError, build_home_account


class InternalHomeView(APIView):
    """Return the account half of the home aggregate for one user.

    ``authentication_classes`` is empty because there is no session cookie on a
    service-to-service call: Kong has already verified the JWT of the original
    browser request and the BFF is the authenticated principal here. The
    ``user_id`` comes from the BFF, which took it from Kong's ``X-User-Id``.
    """

    authentication_classes = []
    permission_classes = [InternalSecretPermission]

    @extend_schema(
        responses={
            200: HomeAccountSerializer,
            401: OpenApiResponse(description="Missing or invalid internal secret."),
            404: OpenApiResponse(description="No user with that id."),
        },
        description=(
            "Internal service-to-service endpoint. Returns the user, profile, "
            "linked accounts and the four account-side onboarding steps for the "
            "given user. The notification unread count is not included; that "
            "table lives in notification_service."
        ),
        summary="Internal home account aggregate",
    )
    def get(self, request, user_id: int):
        try:
            account = build_home_account(user_id)
        except UserNotFoundError:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(account, status=status.HTTP_200_OK)
