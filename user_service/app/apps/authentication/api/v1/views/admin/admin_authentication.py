from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from app.apps.authentication.api.v1.serializers.admin_authentication_serializer import (
    AdminVerificationHistorySerializer,
    AdminAuthenticationOverviewSerializer,
)
from app.apps.authentication.models import AuthMethod, VerificationToken
from app.apps.users.models import User

# pagination
from app.apps.authentication.api.v1.pagination.verification_toekn_pg import (
    VerificationTokenPagination,
)


class AdminAuthenticationView(APIView):
    @extend_schema(
        summary="View user authentication",
        description="Returns authentication methods and verification history for a user.",
        responses={200: AdminAuthenticationOverviewSerializer},
    )
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        authentication_methods = AuthMethod.objects.filter(user=user).order_by("id")
        verification_history = VerificationToken.objects.filter(user=user).order_by(
            "-created_at"
        )

        token_status = request.query_params.get("status")
        if token_status:
            now = timezone.now()
            status_filters = {
                "used": Q(used_at__isnull=False),
                "expired": Q(
                    used_at__isnull=True,
                    revoked_at__isnull=True,
                    expires_at__lte=now,
                ),
                "revoked": Q(used_at__isnull=True, revoked_at__isnull=False),
            }
            if token_status not in status_filters:
                return Response(
                    {
                        "detail": (
                            "Invalid status. Choose one of: used, expired, revoked."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            verification_history = verification_history.filter(
                status_filters[token_status]
            )

        paginator = VerificationTokenPagination()
        token_page = paginator.paginate_queryset(verification_history, request)
        overview_serializer = AdminAuthenticationOverviewSerializer(
            {
                "authentication_methods": authentication_methods,
                "verification_history": token_page,
            }
        )
        response_data = overview_serializer.data
        response_data["verification_history"] = paginator.get_paginated_response(
            AdminVerificationHistorySerializer(token_page, many=True).data
        ).data
        return Response(response_data, status=status.HTTP_200_OK)
