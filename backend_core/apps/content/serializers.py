"""Serializers for the content domain."""

from rest_framework import serializers

from .models import (
    ContentOutput,
    ContentPack,
    ContentPackRequest,
    ContentPackTemplate,
    Template,
    TemplateVersion,
)


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

    def _ensure_global_or_workspace(self, obj, label):
        workspace = self._active_workspace
        if (
            obj is not None
            and workspace is not None
            and obj.workspace_id is not None
            and obj.workspace_id != workspace.id
        ):
            raise serializers.ValidationError(
                f"{label} is not available in the active workspace."
            )
        return obj


class TemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateVersion
        fields = (
            "id",
            "template",
            "version",
            "renderer_type",
            "manifest",
            "required_props",
            "supported_formats",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TemplateSerializer(serializers.ModelSerializer):
    versions = TemplateVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Template
        fields = (
            "id",
            "workspace",
            "template_key",
            "name",
            "description",
            "template_type",
            "status",
            "is_premium",
            "is_system",
            "metadata",
            "versions",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ContentPackTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentPackTemplate
        fields = (
            "id",
            "content_pack",
            "template",
            "output_type",
            "format",
            "required",
            "sort_order",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ContentPackSerializer(serializers.ModelSerializer):
    pack_templates = ContentPackTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = ContentPack
        fields = (
            "id",
            "workspace",
            "pack_key",
            "name",
            "description",
            "pack_type",
            "status",
            "is_premium",
            "pack_templates",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ContentPackRequestSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = ContentPackRequest
        fields = (
            "id",
            "workspace",
            "campaign",
            "track",
            "artist",
            "content_pack",
            "requested_by",
            "status",
            "requested_at",
            "completed_at",
            "failed_at",
            "error_message",
            "usage_event_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "requested_by",
            "status",
            "requested_at",
            "completed_at",
            "failed_at",
            "error_message",
            "usage_event_id",
            "created_at",
            "updated_at",
        )

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")

    def validate_artist(self, value):
        return self._ensure_same_workspace(value, "Artist")

    def validate_content_pack(self, value):
        return self._ensure_global_or_workspace(value, "Content pack")


class ContentOutputSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = ContentOutput
        fields = (
            "id",
            "workspace",
            "campaign",
            "track",
            "artist",
            "content_pack_request",
            "template",
            "template_version",
            "output_type",
            "format",
            "status",
            "title",
            "caption",
            "cta",
            "storage_asset",
            "public_visibility",
            "expires_at",
            "usage_event_id",
            "created_by",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "created_by",
            "usage_event_id",
            "created_at",
            "updated_at",
        )

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")

    def validate_artist(self, value):
        return self._ensure_same_workspace(value, "Artist")

    def validate_storage_asset(self, value):
        return self._ensure_same_workspace(value, "Storage asset")

    def validate_template(self, value):
        return self._ensure_global_or_workspace(value, "Template")
