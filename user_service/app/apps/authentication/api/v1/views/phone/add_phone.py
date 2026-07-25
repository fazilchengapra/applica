from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ...serializers.phone_serializers import RequestPhoneAddSerializer

from app.apps.authentication.services.phone.add_phone import add_phone_number

# exception
from app.apps.authentication.exceptions.phone import (
    PhoneAlreadyVerifiedError,
    PhoneNumberInUseError,
    SamePhoneNumberError
)


class AddPhoneView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = RequestPhoneAddSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid phone number"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            add_phone_number(request.user, serializer.validated_data["phone_number"])
        except (PhoneNumberInUseError, SamePhoneNumberError) as ex:
            return Response({"detail": str(ex)}, status=status.HTTP_400_BAD_REQUEST)
        except PhoneAlreadyVerifiedError as ex:
            return Response({"detail": str(ex)}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(
            {"message": "phone number added success"}, status=status.HTTP_200_OK
        )
