"""Content core models.

Django owns the *product* catalogue of templates and packs, plus the lifecycle
entities (requests, outputs). Real rendering (images, video, PDF, carousels) is
performed later by the Content Renderer / FastAPI — nothing is rendered here.

``Template`` and ``ContentPack`` may be global (``workspace`` null) or
workspace-specific. ``usage_event_id`` is a placeholder hook for the future
billing app (no FK yet, since billing does not exist).
"""

from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    BaseModel,
    CorrelationIdModel,
    CreatedUpdatedByModel,
    WorkspaceOwnedModel,
)


class Template(BaseModel, CreatedUpdatedByModel):
    class TemplateType(models.TextChoices):
        POST = "post", _("Post")
        STORY = "story", _("Story")
        CAROUSEL = "carousel", _("Carousel")
        CAROUSEL_SLIDE = "carousel_slide", _("Carousel slide")
        CARD = "card", _("Card")
        THUMBNAIL = "thumbnail", _("Thumbnail")
        REPORT = "report", _("Report")
        MEDIA_KIT = "media_kit", _("Media kit")
        REEL = "reel", _("Reel")
        SHORT = "short", _("Short")
        WIDGET = "widget", _("Widget")
        EMBED = "embed", _("Embed")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        DEPRECATED = "deprecated", _("Deprecated")
        ARCHIVED = "archived", _("Archived")

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        verbose_name=_("workspace"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="templates",
    )
    template_key = models.SlugField(_("template key"), max_length=120, unique=True)
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    template_type = models.CharField(
        _("template type"), max_length=20, choices=TemplateType.choices
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    is_premium = models.BooleanField(_("premium"), default=False)
    is_system = models.BooleanField(_("system"), default=False)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("template")
        verbose_name_plural = _("templates")
        ordering = ["name"]
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self):
        return self.template_key


class TemplateVersion(BaseModel, CreatedUpdatedByModel):
    class RendererType(models.TextChoices):
        HTML_SVG = "html_svg", _("HTML/SVG")
        SATORI = "satori", _("Satori")
        SHARP = "sharp", _("Sharp")
        PLAYWRIGHT = "playwright", _("Playwright")
        REMOTION_STILL = "remotion_still", _("Remotion still")
        REMOTION_VIDEO = "remotion_video", _("Remotion video")
        PDF = "pdf", _("PDF")
        HTML_EMBED = "html_embed", _("HTML embed")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        DEPRECATED = "deprecated", _("Deprecated")
        ARCHIVED = "archived", _("Archived")

    template = models.ForeignKey(
        Template,
        verbose_name=_("template"),
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version = models.CharField(_("version"), max_length=40)
    renderer_type = models.CharField(
        _("renderer type"), max_length=20, choices=RendererType.choices
    )
    manifest = models.JSONField(_("manifest"), default=dict, blank=True)
    required_props = models.JSONField(_("required props"), default=list, blank=True)
    supported_formats = models.JSONField(
        _("supported formats"), default=list, blank=True
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("template version")
        verbose_name_plural = _("template versions")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version"], name="unique_template_version"
            )
        ]

    def __str__(self):
        return f"{self.template.template_key} v{self.version}"


class ContentPack(BaseModel):
    class PackType(models.TextChoices):
        RELEASE_PACK = "release_pack", _("Release pack")
        MILESTONE_PACK = "milestone_pack", _("Milestone pack")
        WEEKLY_GROWTH_PACK = "weekly_growth_pack", _("Weekly growth pack")
        MONTHLY_RECAP_PACK = "monthly_recap_pack", _("Monthly recap pack")
        COMEBACK_PACK = "comeback_pack", _("Comeback pack")
        RANKING_PACK = "ranking_pack", _("Ranking pack")
        AUTO_MEDIA_KIT = "auto_media_kit", _("Auto media kit")
        LABEL_REPORTING_PACK = "label_reporting_pack", _("Label reporting pack")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        DEPRECATED = "deprecated", _("Deprecated")
        ARCHIVED = "archived", _("Archived")

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        verbose_name=_("workspace"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="content_packs",
    )
    pack_key = models.SlugField(_("pack key"), max_length=120, unique=True)
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    pack_type = models.CharField(
        _("pack type"), max_length=30, choices=PackType.choices
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    is_premium = models.BooleanField(_("premium"), default=False)
    templates = models.ManyToManyField(
        Template, through="ContentPackTemplate", related_name="packs", blank=True
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("content pack")
        verbose_name_plural = _("content packs")
        ordering = ["name"]
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self):
        return self.pack_key


class ContentPackTemplate(BaseModel):
    """A template included in a content pack, with its output settings."""

    content_pack = models.ForeignKey(
        ContentPack,
        verbose_name=_("content pack"),
        on_delete=models.CASCADE,
        related_name="pack_templates",
    )
    template = models.ForeignKey(
        Template,
        verbose_name=_("template"),
        on_delete=models.CASCADE,
        related_name="pack_links",
    )
    output_type = models.CharField(_("output type"), max_length=30)
    format = models.CharField(_("format"), max_length=20, blank=True)
    required = models.BooleanField(_("required"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("content pack template")
        verbose_name_plural = _("content pack templates")
        ordering = ["sort_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_pack", "template", "output_type"],
                name="unique_pack_template_output",
            )
        ]

    def __str__(self):
        return f"{self.content_pack.pack_key} / {self.template.template_key}"


class ContentPackRequest(BaseModel, WorkspaceOwnedModel, CorrelationIdModel):
    """A request to generate a content pack (queued; rendered later elsewhere)."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        QUEUED = "queued", _("Queued")
        PROCESSING = "processing", _("Processing")
        PARTIALLY_COMPLETED = "partially_completed", _("Partially completed")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")

    campaign = models.ForeignKey(
        "campaigns.Campaign",
        verbose_name=_("campaign"),
        on_delete=models.CASCADE,
        related_name="content_pack_requests",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        verbose_name=_("track"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_pack_requests",
    )
    artist = models.ForeignKey(
        "catalogue.Artist",
        verbose_name=_("artist"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_pack_requests",
    )
    content_pack = models.ForeignKey(
        ContentPack,
        verbose_name=_("content pack"),
        on_delete=models.PROTECT,
        related_name="requests",
    )
    requested_by = models.ForeignKey(
        "accounts.User",
        verbose_name=_("requested by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_pack_requests",
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    requested_at = models.DateTimeField(_("requested at"), default=now)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    failed_at = models.DateTimeField(_("failed at"), null=True, blank=True)
    error_message = models.TextField(_("error message"), blank=True)
    # Placeholder hook for the future billing app (no FK yet).
    usage_event_id = models.UUIDField(_("usage event id"), null=True, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("content pack request")
        verbose_name_plural = _("content pack requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        return f"{self.content_pack.pack_key} request ({self.status})"


class ContentOutput(BaseModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    """A generated output entity (placeholder; not rendered here)."""

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        VALIDATING = "validating", _("Validating")
        PROCESSING = "processing", _("Processing")
        RENDERING = "rendering", _("Rendering")
        UPLOADING = "uploading", _("Uploading")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")
        ARCHIVED = "archived", _("Archived")

    class Visibility(models.TextChoices):
        PRIVATE = "private", _("Private")
        WORKSPACE = "workspace", _("Workspace")
        PUBLIC = "public", _("Public")
        UNLISTED = "unlisted", _("Unlisted")

    campaign = models.ForeignKey(
        "campaigns.Campaign",
        verbose_name=_("campaign"),
        on_delete=models.CASCADE,
        related_name="content_outputs",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_outputs",
    )
    artist = models.ForeignKey(
        "catalogue.Artist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_outputs",
    )
    content_pack_request = models.ForeignKey(
        ContentPackRequest,
        verbose_name=_("content pack request"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outputs",
    )
    template = models.ForeignKey(
        Template,
        verbose_name=_("template"),
        on_delete=models.PROTECT,
        related_name="outputs",
    )
    template_version = models.ForeignKey(
        TemplateVersion,
        verbose_name=_("template version"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outputs",
    )
    output_type = models.CharField(_("output type"), max_length=30)
    format = models.CharField(_("format"), max_length=20, blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    title = models.CharField(_("title"), max_length=255, blank=True)
    caption = models.TextField(_("caption"), blank=True)
    cta = models.CharField(_("CTA"), max_length=255, blank=True)
    storage_asset = models.ForeignKey(
        "core.Asset",
        verbose_name=_("storage asset"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_outputs",
    )
    public_visibility = models.CharField(
        _("visibility"),
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    expires_at = models.DateTimeField(_("expires at"), null=True, blank=True)
    usage_event_id = models.UUIDField(_("usage event id"), null=True, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("content output")
        verbose_name_plural = _("content outputs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        return self.title or f"{self.output_type} output ({self.status})"
