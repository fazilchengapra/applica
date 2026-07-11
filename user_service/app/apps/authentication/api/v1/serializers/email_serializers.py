from rest_framework import serializers

class VerifyPhoneOTPSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)

class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=4)


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()

class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()
    
class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=4)
    confirm_password = serializers.CharField(write_only=True, min_length=4)


    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs