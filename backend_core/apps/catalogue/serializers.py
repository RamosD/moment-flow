"""Serializers for the catalogue domain.

Cross-workspace integrity is enforced here: related objects (artist, assets,
track) must belong to the active workspace resolved from X-Workspace-ID.
"""

from rest_framework import serializers

from .models import Artist, Track, TrackPlatformLink
from .utils import extract_youtube_video_id


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


class ArtistSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = (
            "id",
            "workspace",
            "name",
            "slug",
            "country",
            "market",
            "primary_genre",
            "language",
            "bio_short",
            "bio_long",
            "image_asset",
            "status",
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

    def validate_image_asset(self, value):
        return self._ensure_same_workspace(value, "Image asset")


class TrackSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = (
            "id",
            "workspace",
            "artist",
            "title",
            "slug",
            "release_date",
            "track_type",
            "primary_genre",
            "language",
            "market",
            "cover_asset",
            "status",
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

    def validate_artist(self, value):
        return self._ensure_same_workspace(value, "Artist")

    def validate_cover_asset(self, value):
        return self._ensure_same_workspace(value, "Cover asset")


class TrackPlatformLinkSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = TrackPlatformLink
        fields = (
            "id",
            "workspace",
            "track",
            "platform",
            "external_id",
            "url",
            "canonical_url",
            "status",
            "last_validated_at",
            "validation_error",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "last_validated_at",
            "validation_error",
            "created_at",
            "updated_at",
        )
        # external_id is server-derived for YouTube and may be blank for other
        # platforms; uniqueness is enforced explicitly in validate() (and at DB
        # level), so the auto unique-together validator is dropped.
        validators = []

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")

    def validate(self, attrs):
        platform = attrs.get("platform") or getattr(self.instance, "platform", None)
        url = attrs.get("url") or getattr(self.instance, "url", None)

        # Light YouTube validation: extract and store the video id.
        if platform == TrackPlatformLink.Platform.YOUTUBE and url:
            video_id = extract_youtube_video_id(url)
            if not video_id:
                raise serializers.ValidationError(
                    {"url": "Could not extract a YouTube video id from this URL."}
                )
            attrs["external_id"] = video_id

        self._check_unique(attrs, platform)
        return attrs

    def _check_unique(self, attrs, platform):
        external_id = attrs.get("external_id") or getattr(
            self.instance, "external_id", ""
        )
        workspace = self._active_workspace
        if not (external_id and workspace and platform):
            return
        qs = TrackPlatformLink.objects.filter(
            workspace=workspace, platform=platform, external_id=external_id
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"external_id": "This platform link already exists in the workspace."}
            )
