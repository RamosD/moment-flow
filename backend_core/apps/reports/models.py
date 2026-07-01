"""Reports and media kits as core product entities.

Django owns the *requests*, states, history and permissions for reports and media
kits. Real rendering (PDF/ZIP) is delegated to a future renderer/worker — nothing
is rendered here. A report/media kit is created in a non-terminal state and a
``storage_asset`` is attached later when an external worker finishes.

All entities are workspace-owned (multi-tenant). ``status`` carries the lifecycle;
there is no soft delete — an ``archived`` status is used instead.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, WorkspaceOwnedModel


class Report(BaseModel, WorkspaceOwnedModel):
    """A request for / record of a generated report."""

    class ReportType(models.TextChoices):
        WEEKLY_REPORT = "weekly_report", _("Weekly report")
        MONTHLY_REPORT = "monthly_report", _("Monthly report")
        CAMPAIGN_REPORT = "campaign_report", _("Campaign report")
        ARTIST_REPORT = "artist_report", _("Artist report")
        TRACK_REPORT = "track_report", _("Track report")
        LABEL_REPORT = "label_report", _("Label report")
        CATALOGUE_REPORT = "catalogue_report", _("Catalogue report")

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        ARCHIVED = "archived", _("Archived")

    campaign = models.ForeignKey(
        "campaigns.Campaign",
        verbose_name=_("campaign"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    artist = models.ForeignKey(
        "catalogue.Artist",
        verbose_name=_("artist"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        verbose_name=_("track"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    report_type = models.CharField(
        _("report type"), max_length=30, choices=ReportType.choices
    )
    title = models.CharField(_("title"), max_length=255)
    period_start = models.DateField(_("period start"), null=True, blank=True)
    period_end = models.DateField(_("period end"), null=True, blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("requested by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_reports",
    )
    storage_asset = models.ForeignKey(
        "core.Asset",
        verbose_name=_("storage asset"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("report")
        verbose_name_plural = _("reports")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "report_type"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        return self.title or f"{self.report_type} ({self.status})"


class ReportSection(BaseModel, WorkspaceOwnedModel):
    """A structured section of a report (content stored as JSON, not rendered)."""

    report = models.ForeignKey(
        Report,
        verbose_name=_("report"),
        on_delete=models.CASCADE,
        related_name="sections",
    )
    section_key = models.SlugField(_("section key"), max_length=120)
    title = models.CharField(_("title"), max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    content_json = models.JSONField(_("content (JSON)"), default=dict, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("report section")
        verbose_name_plural = _("report sections")
        ordering = ["sort_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "section_key"], name="unique_report_section_key"
            )
        ]
        indexes = [models.Index(fields=["workspace"])]

    def __str__(self):
        return f"{self.report_id} / {self.section_key}"


class MediaKit(BaseModel, WorkspaceOwnedModel):
    """A media kit for an artist (optionally scoped to a campaign/track)."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        GENERATED = "generated", _("Generated")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    class Visibility(models.TextChoices):
        PRIVATE = "private", _("Private")
        WORKSPACE = "workspace", _("Workspace")
        PUBLIC = "public", _("Public")
        UNLISTED = "unlisted", _("Unlisted")

    artist = models.ForeignKey(
        "catalogue.Artist",
        verbose_name=_("artist"),
        on_delete=models.CASCADE,
        related_name="media_kits",
    )
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        verbose_name=_("campaign"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_kits",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        verbose_name=_("track"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_kits",
    )
    title = models.CharField(_("title"), max_length=255)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    public_visibility = models.CharField(
        _("visibility"),
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    storage_asset = models.ForeignKey(
        "core.Asset",
        verbose_name=_("storage asset"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_kits",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_media_kits",
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("media kit")
        verbose_name_plural = _("media kits")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["artist"]),
        ]

    def __str__(self):
        return self.title or f"Media kit ({self.status})"


class MediaKitItem(BaseModel, WorkspaceOwnedModel):
    """An item inside a media kit (bio, stats, image, link, …)."""

    class ItemType(models.TextChoices):
        BIO = "bio", _("Bio")
        STATS = "stats", _("Stats")
        IMAGE = "image", _("Image")
        TRACK = "track", _("Track")
        LINK = "link", _("Link")
        PRESS_QUOTE = "press_quote", _("Press quote")
        CONTACT = "contact", _("Contact")
        ACHIEVEMENT = "achievement", _("Achievement")
        OTHER = "other", _("Other")

    media_kit = models.ForeignKey(
        MediaKit,
        verbose_name=_("media kit"),
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(
        _("item type"), max_length=20, choices=ItemType.choices, default=ItemType.OTHER
    )
    title = models.CharField(_("title"), max_length=255, blank=True)
    content = models.TextField(_("content"), blank=True)
    asset = models.ForeignKey(
        "core.Asset",
        verbose_name=_("asset"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_kit_items",
    )
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("media kit item")
        verbose_name_plural = _("media kit items")
        ordering = ["sort_order", "created_at"]
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["media_kit"]),
        ]

    def __str__(self):
        return f"{self.media_kit_id} / {self.item_type}"
