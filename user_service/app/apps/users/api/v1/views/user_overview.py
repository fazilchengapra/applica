from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from app.apps.users.models import User

from ..serializers.user_overview_serializer import UserOverviewSerializer


class UserOverviewView(APIView):
    @extend_schema(
        summary="View user overview",
        description="Returns the account overview for a single user.",
        responses={200: UserOverviewSerializer},
    )
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = UserOverviewSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)