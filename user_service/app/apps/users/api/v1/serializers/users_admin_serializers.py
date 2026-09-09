from rest_framework import serializers
from app.apps.users.models import User

class UserListSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_active"]

    def get_username(self, obj):
        email = (obj.email or "").strip()
        if not email:
            return ""
        return email.split("@", 1)[0]

class UserActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']