"""Campaign models: Campaign, CampaignTrack and CampaignGoal.

A campaign is the product's central unit of value. It belongs to a workspace and
references an artist (required) and optionally a track, both from the same
workspace (enforced in the serializers). Heavy analytics (metrics/moments/
insights) are out of scope here.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    BaseModel,
    CreatedUpdatedByModel,
    SoftDeleteModel,
    WorkspaceOwnedModel,
)


class Campaign(BaseModel, SoftDeleteModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    class CampaignType(models.TextChoices):
        SINGLE_RELEASE = "single_release", _("Single release")
        MUSIC_VIDEO_RELEASE = "music_video_release", _("Music video release")
        ALBUM_RELEASE = "album_release", _("Album release")
        MILESTONE_CAMPAIGN = "milestone_campaign", _("Milestone campaign")
        COMEBACK_CAMPAIGN = "comeback_campaign", _("Comeback campaign")
        WEEKLY_GROWTH_CAMPAIGN = "weekly_growth_campaign", _("Weekly growth campaign")
        CATALOGUE_PUSH = "catalogue_push", _("Catalogue push")
        MEDIA_CAMPAIGN = "media_campaign", _("Media campaign")
        CUSTOM = "custom", _("Custom")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SCHEDULED = "scheduled", _("Scheduled")
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        COMPLETED = "completed", _("Completed")
        ARCHIVED = "archived", _("Archived")

    artist = models.ForeignKey(
        "catalogue.Artist",
        verbose_name=_("artist"),
        on_delete=models.CASCADE,
        related_name="campaigns",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        verbose_name=_("track"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)
    campaign_type = models.CharField(
        _("campaign type"),
        max_length=30,
        choices=CampaignType.choices,
        default=CampaignType.SINGLE_RELEASE,
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    start_date = models.DateField(_("start date"), null=True, blank=True)
    end_date = models.DateField(_("end date"), null=True, blank=True)
    primary_goal = models.CharField(_("primary goal"), max_length=120, blank=True)
    description = models.TextField(_("description"), blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("campaign")
        verbose_name_plural = _("campaigns")
        ordering = ["-created_at"]
        base_manager_name = "all_objects"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_campaign_slug_per_workspace",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["artist"]),
        ]

    def __str__(self):
        return self.name


class CampaignTrack(BaseModel, WorkspaceOwnedModel):
    """A track attached to a campaign (a campaign may have several)."""

    class Role(models.TextChoices):
        PRIMARY = "primary", _("Primary")
        SECONDARY = "secondary", _("Secondary")
        REFERENCE = "reference", _("Reference")
        CATALOGUE_ITEM = "catalogue_item", _("Catalogue item")

    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("campaign"),
        on_delete=models.CASCADE,
        related_name="campaign_tracks",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        verbose_name=_("track"),
        on_delete=models.CASCADE,
        related_name="campaign_tracks",
    )
    role = models.CharField(
        _("role"), max_length=20, choices=Role.choices, default=Role.PRIMARY
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("campaign track")
        verbose_name_plural = _("campaign tracks")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "track"],
                name="unique_track_per_campaign",
            )
        ]
        indexes = [models.Index(fields=["workspace"])]

    def __str__(self):
        return f"{self.campaign} / {self.track} ({self.role})"


class CampaignGoal(BaseModel, WorkspaceOwnedModel):
    """A measurable objective for a campaign."""

    class GoalType(models.TextChoices):
        VIEWS = "views", _("Views")
        CLICKS = "clicks", _("Clicks")
        CONTENT_OUTPUTS = "content_outputs", _("Content outputs")
        MILESTONE = "milestone", _("Milestone")
        REPORTS = "reports", _("Reports")
        ENGAGEMENT = "engagement", _("Engagement")
        CUSTOM = "custom", _("Custom")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        ACHIEVED = "achieved", _("Achieved")
        MISSED = "missed", _("Missed")
        CANCELLED = "cancelled", _("Cancelled")

    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("campaign"),
        on_delete=models.CASCADE,
        related_name="goals",
    )
    goal_type = models.CharField(
        _("goal type"), max_length=20, choices=GoalType.choices
    )
    target_value = models.DecimalField(
        _("target value"), max_digits=20, decimal_places=2, null=True, blank=True
    )
    current_value = models.DecimalField(
        _("current value"), max_digits=20, decimal_places=2, default=0
    )
    unit = models.CharField(_("unit"), max_length=40, blank=True)
    deadline = models.DateField(_("deadline"), null=True, blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("campaign goal")
        verbose_name_plural = _("campaign goals")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        return f"{self.campaign} / {self.goal_type}"
