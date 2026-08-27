import logging
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from django.contrib.auth import get_user_model
from app.apps.notifications.services import create_and_push, push_cv_status

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

        try:
            user = User.objects.get(id=data["user_id"])
        except User.DoesNotExist:
            logger.warning(
                "Notification dispatch: unknown user_id %s", data.get("user_id")
            )
            return Response(
                {"detail": "user not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if data["event_type"] == "cv.processing":
            push_cv_status(user_id=user.id, cv_id=data["cv_id"], status="processing")

        elif data["event_type"] in ("cv.completed", "cv.failed"):
            push_cv_status(
                user_id=user.id,
                cv_id=data["cv_id"],
                status=data["status"].split(".")[-1],
            )
            create_and_push(
                user=user,
                type=data[
                    "event_type"
                ],  # SNS payload's "event_type" -> your "type" param
                title=data["title"],
                body=data["body"],
                metadata=data.get("metadata", {}),
            )
        else:
            create_and_push(
                user=user,
                type=data[
                    "event_type"
                ],  # SNS payload's "event_type" -> your "type" param
                title=data["title"],
                body=data["body"],
                metadata=data.get("metadata", {}),
            )

        return Response(status=status.HTTP_201_CREATED)
