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
    SamePhoneNumberError,
)

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class AddPhoneView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RequestPhoneAddSerializer,
        responses={
            200: OpenApiResponse(
                description="Phone number added successfully.",
                examples=[
                    OpenApiExample(
                        "Success", value={"message": "phone number added success"}
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Invalid phone number, already in use by another account, or same as current phone.",
                examples=[
                    OpenApiExample(
                        "Invalid format", value={"detail": "Invalid phone number"}
                    ),
                    OpenApiExample(
                        "Already in use",
                        value={"detail": "This phone number is already in use."},
                    ),
                    OpenApiExample(
                        "Same number",
                        value={
                            "detail": "New phone number must be different from your current one."
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Phone number is already verified on this account.",
                examples=[
                    OpenApiExample(
                        "Already verified",
                        value={"detail": "Phone number is already verified."},
                    )
                ],
            ),
        },
        description="Adds or replaces the authenticated user's phone number, pending verification.",
        summary="Add phone number",
    )
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
