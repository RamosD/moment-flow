"""Serializers for the campaigns domain (with cross-workspace integrity)."""

from rest_framework import serializers

from .models import Campaign, CampaignGoal, CampaignTrack


class _WorkspaceContextMixin:
    """Validate that related FKs belong to the active workspace."""

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


class CampaignSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = (
            "id",
            "workspace",
            "artist",
            "track",
            "name",
            "slug",
            "campaign_type",
            "status",
            "start_date",
            "end_date",
            "primary_goal",
            "description",
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

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")


class CampaignTrackSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = CampaignTrack
        fields = (
            "id",
            "workspace",
            "campaign",
            "track",
            "role",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "workspace", "created_at", "updated_at")

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")

    def validate_track(self, value):
        return self._ensure_same_workspace(value, "Track")


class CampaignIntelligenceResultSerializer(serializers.Serializer):
    """The engine's ``result`` block (documentation/schema only)."""

    analysis = serializers.DictField(required=False)
    scores = serializers.DictField(required=False)
    grade = serializers.CharField(required=False, allow_null=True)
    moments = serializers.ListField(required=False)
    recommendations = serializers.ListField(required=False)
    summary = serializers.CharField(required=False, allow_blank=True)


class CampaignIntelligenceResponseSerializer(serializers.Serializer):
    """Normalized campaign-intelligence response (documentation/schema only).

    The endpoint returns the service outcome as a plain dict; this serializer
    exists so drf-spectacular can document the response shape.
    """

    status = serializers.CharField()
    source = serializers.ChoiceField(choices=["engine", "dry_run"])
    engine = serializers.CharField(allow_blank=True)
    engine_version = serializers.CharField(allow_blank=True)
    request_id = serializers.CharField()
    workspace_id = serializers.CharField()
    campaign_id = serializers.CharField()
    result = CampaignIntelligenceResultSerializer()
    explanations = serializers.ListField(child=serializers.DictField(), required=False)
    warnings = serializers.ListField(child=serializers.DictField(), required=False)
    metadata = serializers.DictField(required=False)
    generated_at = serializers.CharField(allow_blank=True)


class CampaignGoalSerializer(_WorkspaceContextMixin, serializers.ModelSerializer):
    class Meta:
        model = CampaignGoal
        fields = (
            "id",
            "workspace",
            "campaign",
            "goal_type",
            "target_value",
            "current_value",
            "unit",
            "deadline",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "workspace", "created_at", "updated_at")

    def validate_campaign(self, value):
        return self._ensure_same_workspace(value, "Campaign")
