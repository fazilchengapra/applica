from rest_framework import serializers
from app.apps.users.models import User

class MeProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    avatar_url = serializers.URLField()


class MeSerializer(serializers.ModelSerializer):
    profile = MeProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "is_email_verified",
            "is_phone_verified",
            "date_joined",
            "profile"
        ]
