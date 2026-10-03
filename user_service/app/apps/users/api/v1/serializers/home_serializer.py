"""Response shape for the internal home-account aggregate.

This is the contract between user_service and the BFF in ai_service. It is
deliberately flat and versioned by convention: the BFF composes the final
``onboarding.percent`` and the ``upload_cv`` step from its own data, so only
the account-side facts cross the boundary.
"""

from rest_framework import serializers


class HomeUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    phone_number = serializers.CharField(allow_null=True)
    is_email_verified = serializers.BooleanField()
    is_phone_verified = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    last_login = serializers.DateTimeField(allow_null=True)
    is_staff = serializers.BooleanField()
    roles = serializers.ListField(child=serializers.CharField())


class HomeProfileSerializer(serializers.Serializer):
    display_name = serializers.CharField(allow_blank=True)
    avatar_url = serializers.CharField(allow_blank=True)
    bio = serializers.CharField(allow_blank=True)
    country = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    timezone = serializers.CharField(allow_blank=True)
    locale = serializers.CharField(allow_blank=True)


class HomeAccountStepsSerializer(serializers.Serializer):
    """The four steps user_service can evaluate; ``upload_cv`` is the BFF's."""

    verify_email = serializers.BooleanField()
    verify_phone = serializers.BooleanField()
    add_photo = serializers.BooleanField()
    complete_profile = serializers.BooleanField()


class HomeLinkedAccountSerializer(serializers.Serializer):
    provider = serializers.CharField()
    is_verified = serializers.BooleanField()
    is_active = serializers.BooleanField()
    linked_at = serializers.DateTimeField()


class HomeAccountSerializer(serializers.Serializer):
    """Top-level envelope returned to the BFF.

    There is no ``notifications`` key: the notifications table belongs to
    notification_service, and the BFF reads the unread count from there so each
    service returns the state it actually owns.
    """

    user = HomeUserSerializer()
    profile = HomeProfileSerializer()
    account_steps = HomeAccountStepsSerializer()
    linked_accounts = HomeLinkedAccountSerializer(many=True)
