from rest_framework import serializers

class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=4)