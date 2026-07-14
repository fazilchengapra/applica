from rest_framework.views import APIView
from rest_framework.response import Response

from ...serializers.email_serializers import EmailChangeReqSerializer
from rest_framework.permissions import IsAuthenticated

from app.apps.authentication.services.email.email_change_request import (
    request_email_change,
)

from app.apps.authentication.exceptions.email import (
    EmailInUseError,
    EmailChangeInvalidError,
    EmailNotVerifiedError,
    SameEmailError,
)
from app.apps.authentication.exceptions.token import TokenRequestCooldownError
from rest_framework import status


class EmailChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmailChangeReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_email_change(
                user=request.user,
                new_email=serializer.validated_data["new_email"],
            )
        except TokenRequestCooldownError as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except (
            EmailInUseError,
            EmailChangeInvalidError,
            EmailNotVerifiedError,
            SameEmailError,
        ) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": "Verification codes sent to both your current and new email."},
            status=status.HTTP_200_OK,
        )