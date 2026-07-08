from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class UserView(APIView):
    """
    API view for user creation.
    """

    def get(self, request, *args, **kwargs):
        return Response({"message": "User created successfully."}, status=status.HTTP_201_CREATED)