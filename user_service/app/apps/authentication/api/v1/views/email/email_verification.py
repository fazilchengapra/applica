from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ...serializers.email_serializers import VerifyEmailSerializer

from .....services.email.email_verification_service import verify_email

# exception
from .....exceptions import EmailVerificationInvalidError

class VerifyEmailView(APIView):

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'detail':'validation error', 'error':serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            verify_email(user_id=serializer.validated_data['uid'], raw_token=serializer.validated_data['token'])

        except EmailVerificationInvalidError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Email verification success'}, status=status.HTTP_200_OK)