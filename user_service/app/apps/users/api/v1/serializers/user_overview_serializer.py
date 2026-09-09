from rest_framework import serializers

from app.apps.users.models import User


class UserOverviewContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "phone_number"]


class UserOverviewAccountSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    is_deactivated = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["status", "is_active", "is_deactivated", "deactivated_at"]

    def get_status(self, obj):
        if obj.deactivated_at is not None:
            return "deactivated"
        return "active" if obj.is_active else "inactive"

    def get_is_deactivated(self, obj):
        return obj.deactivated_at is not None


class UserOverviewPermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["is_staff", "is_superuser"]


class UserOverviewVerificationSerializer(serializers.ModelSerializer):
    email_verified = serializers.BooleanField(source="is_email_verified")
    phone_verified = serializers.BooleanField(source="is_phone_verified")

    class Meta:
        model = User
        fields = ["email_verified", "phone_verified"]


class UserOverviewTimestampsSerializer(serializers.ModelSerializer):
    joined_at = serializers.DateTimeField(source="date_joined")
    last_updated = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = User
        fields = ["joined_at", "last_login", "last_updated"]


class UserOverviewSerializer(serializers.ModelSerializer):
    contact = UserOverviewContactSerializer(source="*")
    account = UserOverviewAccountSerializer(source="*")
    permissions = UserOverviewPermissionsSerializer(source="*")
    verification = UserOverviewVerificationSerializer(source="*")
    timestamps = UserOverviewTimestampsSerializer(source="*")

    class Meta:
        model = User
        fields = [
            "id",
            "contact",
            "account",
            "permissions",
            "verification",
            "timestamps",
        ]
