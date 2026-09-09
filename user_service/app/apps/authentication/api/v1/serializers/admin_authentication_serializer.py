from django.utils import timezone
from rest_framework import serializers

from app.apps.authentication.models import AuthMethod, VerificationToken


class AdminAuthenticationVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthMethod
        fields = ["is_verified"]


class AdminAuthenticationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthMethod
        fields = ["is_active"]


class AdminAuthenticationMethodSerializer(serializers.ModelSerializer):
    verification = AdminAuthenticationVerificationSerializer(source="*")
    status = AdminAuthenticationStatusSerializer(source="*")

    class Meta:
        model = AuthMethod
        fields = [
            "provider",
            "provider_email",
            "verification",
            "status",
            "linked_at",
            "last_used_at",
        ]


class AdminVerificationHistorySerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = VerificationToken
        fields = ["type", "status", "created_at", "expires_at"]

    def get_status(self, obj):
        if obj.used_at is not None:
            return "used"
        if obj.revoked_at is not None:
            return "revoked"
        if obj.expires_at <= timezone.now():
            return "expired"
        return "active"


class AdminAuthenticationOverviewSerializer(serializers.Serializer):
    authentication_methods = AdminAuthenticationMethodSerializer(many=True)
    verification_history = AdminVerificationHistorySerializer(many=True)
