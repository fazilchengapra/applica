from rest_framework import serializers

from app.apps.profiles.models import Profile


class AdminProfileNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["first_name", "last_name", "display_name"]


class AdminProfileDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["avatar_url", "bio"]


class AdminProfilePersonalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["date_of_birth", "gender"]


class AdminProfileLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["country", "city", "timezone"]


class AdminProfileOverviewSerializer(serializers.ModelSerializer):
    name = AdminProfileNameSerializer(source="*")
    profile = AdminProfileDetailsSerializer(source="*")
    personal = AdminProfilePersonalSerializer(source="*")
    location = AdminProfileLocationSerializer(source="*")

    class Meta:
        model = Profile
        fields = ["name", "profile", "personal", "location", "locale"]
