from rest_framework import serializers
from app.apps.users.models import User

class MeProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(allow_null=True)
    last_name = serializers.CharField(allow_null=True)
    avatar_url = serializers.URLField(allow_null=True)


class MeSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "is_email_verified",
            "is_phone_verified",
            "date_joined",
            "profile",
            "is_staff"
        ]

    def get_profile(self, obj):
        profile = getattr(obj, "profile", None)
        if profile is None:
            return None
        return MeProfileSerializer(profile).data

