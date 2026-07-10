from rest_framework import serializers

class VerifyPhoneOTPSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)