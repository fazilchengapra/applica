from rest_framework import serializers


class RequestLoginOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class VerifyLoginOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(min_length=6, max_length=6)


class RequestPhoneChangeSerializer(serializers.Serializer):
    new_phone_number = serializers.CharField()


class VerifyPhoneChangeSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)