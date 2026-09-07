import logging
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from django.contrib.auth import get_user_model
from app.apps.notifications.services import create_and_push

logger = logging.getLogger(__name__)
User = get_user_model()


class InternalSecretPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        print(view)
        return request.headers.get("X-Internal-Secret") == os.getenv(
            "INTERNAL_SHARED_SECRET"
        )


class NotificationDispatchView(APIView):
    permission_classes = [InternalSecretPermission]
    authentication_classes = []

    def post(self, request):
        data = request.data
        print(data)
        try:
            user = User.objects.get(id=data["user_id"])
        except User.DoesNotExist:
            logger.warning(
                "Notification dispatch: unknown user_id %s", data.get("user_id")
            )
            return Response(
                {"detail": "user not found"}, status=status.HTTP_404_NOT_FOUND
            )

        create_and_push(
            user=user,
            type=data["event_type"],
            title=data["title"],
            body=data["body"],
            metadata=data.get("metadata", {}),
        )

        return Response(status=status.HTTP_201_CREATED)
