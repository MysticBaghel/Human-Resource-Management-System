"""Serializers for the account endpoints."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """The shape of a user everywhere in the API."""

    class Meta:
        model = User
        fields = ["id", "email", "role", "is_active", "date_joined"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """Validate credentials without touching the session.

    The view owns session creation so the serializer stays reusable and
    testable on its own.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        trim_whitespace=False,
    )

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )
        if user is None:
            # One message for both cases, so the response cannot be used to
            # discover which email addresses exist.
            raise serializers.ValidationError("Invalid email or password.")

        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        trim_whitespace=False,
    )

    def validate(self, attrs: dict) -> dict:
        from django.utils.http import urlsafe_base64_decode

        try:
            user_id = urlsafe_base64_decode(attrs["uid"]).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("This reset link is invalid.")

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("This reset link is invalid or has expired.")

        # Same message as a bad token: confirming that an account exists but is
        # deactivated would leak which addresses are real.
        if not user.is_active:
            raise serializers.ValidationError("This reset link is invalid or has expired.")

        validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs

    @staticmethod
    def build_uid(user) -> str:
        return urlsafe_base64_encode(force_bytes(user.pk))
