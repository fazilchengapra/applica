from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField


class RequestLoginOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class VerifyLoginOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(min_length=6, max_length=6)


class RequestPhoneChangeSerializer(serializers.Serializer):
    new_phone_number = PhoneNumberField()


class VerifyPhoneChangeSerializer(serializers.Serializer):
    old_code = serializers.CharField(min_length=6, max_length=6)
    new_code = serializers.CharField(min_length=6, max_length=6)

class VerifyPhoneOTPSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)

class RequestPhoneAddSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()