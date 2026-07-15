from rest_framework import serializers

from app.apps.profiles.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["display_name", "avatar_url"]
