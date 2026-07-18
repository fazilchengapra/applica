from rest_framework import serializers

from app.apps.profiles.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    is_email_verified = serializers.BooleanField(
        source="user.is_email_verified", read_only=True
    )
    is_phone_verified = serializers.BooleanField(
        source="user.is_phone_verified", read_only=True
    )

    class Meta:
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "display_name",
            "avatar_url",
            "bio",
            "date_of_birth",
            "gender",
            "country",
            "city",
            "timezone",
            "locale",
            "email",
            "phone_number",
            "is_email_verified",
            "is_phone_verified",
        ]
        read_only_fields = ["display_name", "avatar_url"]
