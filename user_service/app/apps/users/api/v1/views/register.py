from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError

from ..serializers.register_serializer import RegisterSerializer
from app.apps.users.services.register_service import register_user


class UserView(APIView):
    """
    API view for user creation.
    """

    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        # validating the giving data
        if not serializer.is_valid():
            return Response(
                {"message": "Data validation error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = register_user(**serializer.validated_data)

        except IntegrityError:
            return Response(
                {"detail": "A user with this email or phone number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "message": "user created success!",
                "data": {
                    "id": user.id,
                    "email": user.email,
                    "phone_number": str(user.phone_number),
                },
            }
        )
