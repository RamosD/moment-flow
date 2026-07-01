"""Serializers for the smart links domain."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import SmartLink, SmartLinkClick, SmartLinkDestination


class _WorkspaceContextMixin:
    @property
    def _active_workspace(self):
        request = self.context.get("request")
        return getattr(request, "workspace", None)

    def _ensure_same_workspace(self, obj, label):
        workspace = self._active_workspace
        if obj is not None and workspace is not None and obj.workspace_id != workspace.id:
            raise serializers.ValidationError(
                f"{label} must belong to the active workspace."
            )
        return obj


class SmartLinkSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = SmartLink
        fields = (
            "id",
            "workspace",
            "campaign",
            "track",
            "artist",
            "slug",
            "title",
            "description",
            "status",
            "branding_enabled",
            "created_by",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "slug",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")

    def validate_artist(self, value):
        return self._ensure_same_workspace(value, "Artist")


class SmartLinkDestinationSerializer(
    _WorkspaceContextMixin, serializers.ModelSerializer
):
    class Meta:
        model = SmartLinkDestination
        fields = (
            "id",
            "workspace",
            "smart_link",
            "platform",
            "label",
            "url",
            "sort_order",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "workspace", "created_at", "updated_at")

    def validate_smart_link(self, value):
        return self._ensure_same_workspace(value, "Smart link")


class SmartLinkClickSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartLinkClick
        fields = (
            "id",
            "workspace",
            "smart_link",
            "destination",
            "content_output",
            "campaign",
            "track",
            "clicked_at",
            "referrer",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "country",
            "device_type",
            "browser",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class PublicSmartLinkDestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartLinkDestination
        fields = ("id", "platform", "label", "url", "sort_order")


class PublicSmartLinkSerializer(serializers.ModelSerializer):
    destinations = serializers.SerializerMethodField()

    class Meta:
        model = SmartLink
        fields = ("id", "slug", "title", "description", "branding_enabled", "destinations")

    @extend_schema_field(PublicSmartLinkDestinationSerializer(many=True))
    def get_destinations(self, obj):
        active = obj.destinations.filter(is_active=True).order_by("sort_order")
        return PublicSmartLinkDestinationSerializer(active, many=True).data
