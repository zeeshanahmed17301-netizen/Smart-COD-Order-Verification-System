"""Serializers for accounts: signup, login, profile, onboarding."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .models import MerchantProfile

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    """Register a new merchant user."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name",
            "password", "password2",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data: dict) -> User:
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # Auto-create empty merchant profile
        MerchantProfile.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Read-only user info."""

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name",
            "is_onboarded", "date_joined",
        ]
        read_only_fields = fields


class MerchantProfileSerializer(serializers.ModelSerializer):
    """Merchant profile for onboarding and settings."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = MerchantProfile
        fields = [
            "id", "user", "store_name", "category", "country",
            "whatsapp_number", "whatsapp_api_key", "language",
            "auto_send", "auto_cancel", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class OnboardingSerializer(serializers.ModelSerializer):
    """Onboarding wizard data — updates merchant profile."""

    class Meta:
        model = MerchantProfile
        fields = [
            "store_name", "category", "country",
            "language", "auto_send", "auto_cancel",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Change password with old password verification."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Update user profile fields."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request a password-reset link for an email address."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm a password reset using the uid + token from the email link."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

    def validate(self, attrs: dict) -> dict:
        try:
            user_pk = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError({"uid": "Invalid reset link."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"token": "This reset link is invalid or has expired."}
            )

        attrs["user"] = user
        return attrs

    def save(self) -> User:
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
