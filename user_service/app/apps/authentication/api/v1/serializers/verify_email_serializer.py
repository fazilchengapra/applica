from rest_framework import serializers


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()
