"""Serializers for the authenticated user's profile."""

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of the authenticated user."""

    is_email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "display_name",
            "avatar_url",
            "preferred_language",
            "timezone",
            "email_verified_at",
            "is_email_verified",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Writable serializer for the user's own basic profile fields."""

    class Meta:
        model = User
        fields = (
            "full_name",
            "display_name",
            "avatar_url",
            "preferred_language",
            "timezone",
        )
