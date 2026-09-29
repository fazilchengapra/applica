import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from app.apps.common.permissions import InternalSecretPermission
from app.apps.notifications.services import create_and_push

logger = logging.getLogger(__name__)
User = get_user_model()


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
