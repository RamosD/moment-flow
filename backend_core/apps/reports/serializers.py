"""Serializers for the reports/media-kit domain.

Cross-workspace integrity is enforced here: every related object (campaign,
artist, track, asset, parent report/media kit) must belong to the active
workspace resolved from ``X-Workspace-ID``.
"""

from rest_framework import serializers

from .models import MediaKit, MediaKitItem, Report, ReportSection


class _WorkspaceContextMixin:
    """Helpers for validating that related FKs share the active workspace."""

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


class ReportSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "workspace",
            "campaign",
            "artist",
            "track",
            "report_type",
            "title",
            "period_start",
            "period_end",
            "status",
            "requested_by",
            "storage_asset",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "requested_by",
            "created_at",
            "updated_at",
        )

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")

    def validate_artist(self, value):
        return self._ensure_same_workspace(value, "Artist")

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")

    def validate_storage_asset(self, value):
        return self._ensure_same_workspace(value, "Storage asset")


class ReportSectionSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = ReportSection
        fields = (
            "id",
            "workspace",
            "report",
            "section_key",
            "title",
            "sort_order",
            "content_json",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "workspace", "created_at", "updated_at")

    def validate_report(self, value):
        return self._ensure_same_workspace(value, "Report")


class MediaKitItemSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = MediaKitItem
        fields = (
            "id",
            "workspace",
            "media_kit",
            "item_type",
            "title",
            "content",
            "asset",
            "sort_order",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "workspace", "created_at", "updated_at")

    def validate_media_kit(self, value):
        return self._ensure_same_workspace(value, "Media kit")

    def validate_asset(self, value):
        return self._ensure_same_workspace(value, "Asset")


class MediaKitSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    items = MediaKitItemSerializer(many=True, read_only=True)

    class Meta:
        model = MediaKit
        fields = (
            "id",
            "workspace",
            "artist",
            "campaign",
            "track",
            "title",
            "status",
            "public_visibility",
            "storage_asset",
            "created_by",
            "items",
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

    def validate_artist(self, value):
        return self._ensure_same_workspace(value, "Artist")

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")

    def validate_storage_asset(self, value):
        return self._ensure_same_workspace(value, "Storage asset")
