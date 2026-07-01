"""Serializers for the notifications domain."""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "workspace",
            "user",
            "notification_type",
            "title",
            "message",
            "related_entity_type",
            "related_entity_id",
            "status",
            "read_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "user",
            "status",
            "read_at",
            "created_at",
            "updated_at",
        )
