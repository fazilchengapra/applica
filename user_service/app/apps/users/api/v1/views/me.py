# user_mgmt/api/v1/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from ..serializers.me_serializer import MeSerializer
from ..serializers.dlt_account_serializer import DeleteAccountSerializer
from app.apps.users.services.me_service import get_current_user
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from app.apps.users.services.acc_dlt_service import delete_account
from app.apps.users.exception import InvalidPasswordError


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_current_user(request.user.id)
        serializer = MeSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        serializer = DeleteAccountSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({"detail": "Validation error", "error": serializer.errors})

        try:
            delete_account(
                user=request.user,
                password=serializer.validated_data["password"],
            )
        except InvalidPasswordError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response
