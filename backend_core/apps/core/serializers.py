"""Serializers for core entities."""

from rest_framework import serializers

from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    """Read/create representation of an Asset.

    ``workspace`` is taken from the active workspace (X-Workspace-ID) and
    ``created_by`` from the request user; both are server-managed.
    """

    class Meta:
        model = Asset
        fields = (
            "id",
            "workspace",
            "asset_type",
            "storage_provider",
            "bucket",
            "storage_key",
            "file_name",
            "mime_type",
            "file_size_bytes",
            "width",
            "height",
            "duration_seconds",
            "checksum",
            "created_by",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "created_by",
            "created_at",
            "updated_at",
        )
