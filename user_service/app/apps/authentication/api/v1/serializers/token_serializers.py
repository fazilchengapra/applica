from rest_framework import serializers

class EmailChangeConfirmationSerializer(serializers.Serializer):
    token = serializers.CharField()