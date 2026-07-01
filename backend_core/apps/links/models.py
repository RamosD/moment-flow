"""Smart link models: SmartLink, SmartLinkDestination and SmartLinkClick.

Slugs are globally unique (public URLs have no workspace context). Click tracking
is privacy-preserving: IP and user-agent are stored only as salted hashes.
"""

from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    BaseModel,
    CreatedUpdatedByModel,
    SoftDeleteModel,
    WorkspaceOwnedModel,
)


class SmartLink(BaseModel, SoftDeleteModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        EXPIRED = "expired", _("Expired")
        ARCHIVED = "archived", _("Archived")

    campaign = models.ForeignKey(
        "campaigns.Campaign",
        verbose_name=_("campaign"),
        on_delete=models.CASCADE,
        related_name="smart_links",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="smart_links",
    )
    artist = models.ForeignKey(
        "catalogue.Artist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="smart_links",
    )
    slug = models.SlugField(_("slug"), max_length=255, unique=True)
    title = models.CharField(_("title"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    branding_enabled = models.BooleanField(_("branding enabled"), default=False)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("smart link")
        verbose_name_plural = _("smart links")
        ordering = ["-created_at"]
        base_manager_name = "all_objects"
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self):
        return self.slug


class SmartLinkDestination(BaseModel, WorkspaceOwnedModel):
    class Platform(models.TextChoices):
        YOUTUBE = "youtube", _("YouTube")
        SPOTIFY = "spotify", _("Spotify")
        APPLE_MUSIC = "apple_music", _("Apple Music")
        DEEZER = "deezer", _("Deezer")
        AUDIOMACK = "audiomack", _("Audiomack")
        SOUNDCLOUD = "soundcloud", _("SoundCloud")
        BOOMPLAY = "boomplay", _("Boomplay")
        INSTAGRAM = "instagram", _("Instagram")
        TIKTOK = "tiktok", _("TikTok")
        WEBSITE = "website", _("Website")
        CUSTOM = "custom", _("Custom")

    smart_link = models.ForeignKey(
        SmartLink,
        verbose_name=_("smart link"),
        on_delete=models.CASCADE,
        related_name="destinations",
    )
    platform = models.CharField(_("platform"), max_length=20, choices=Platform.choices)
    label = models.CharField(_("label"), max_length=120, blank=True)
    url = models.URLField(_("url"), max_length=1000)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("smart link destination")
        verbose_name_plural = _("smart link destinations")
        ordering = ["sort_order", "created_at"]
        indexes = [models.Index(fields=["smart_link", "is_active"])]

    def __str__(self):
        return f"{self.smart_link.slug} -> {self.platform}"


class SmartLinkClick(BaseModel, WorkspaceOwnedModel):
    """A single click/open event on a smart link (privacy-preserving)."""

    smart_link = models.ForeignKey(
        SmartLink,
        verbose_name=_("smart link"),
        on_delete=models.CASCADE,
        related_name="clicks",
    )
    destination = models.ForeignKey(
        SmartLinkDestination,
        verbose_name=_("destination"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clicks",
    )
    content_output = models.ForeignKey(
        "content.ContentOutput",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="link_clicks",
    )
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        on_delete=models.CASCADE,
        related_name="smart_link_clicks",
    )
    track = models.ForeignKey(
        "catalogue.Track",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="smart_link_clicks",
    )
    clicked_at = models.DateTimeField(_("clicked at"), default=now)
    referrer = models.URLField(_("referrer"), max_length=1000, blank=True)
    utm_source = models.CharField(_("utm source"), max_length=255, blank=True)
    utm_medium = models.CharField(_("utm medium"), max_length=255, blank=True)
    utm_campaign = models.CharField(_("utm campaign"), max_length=255, blank=True)
    utm_content = models.CharField(_("utm content"), max_length=255, blank=True)
    country = models.CharField(_("country"), max_length=2, blank=True)
    device_type = models.CharField(_("device type"), max_length=20, blank=True)
    browser = models.CharField(_("browser"), max_length=40, blank=True)
    ip_hash = models.CharField(_("ip hash"), max_length=64, blank=True)
    user_agent_hash = models.CharField(_("user agent hash"), max_length=64, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("smart link click")
        verbose_name_plural = _("smart link clicks")
        ordering = ["-clicked_at"]
        indexes = [
            models.Index(fields=["workspace", "smart_link"]),
            models.Index(fields=["smart_link", "clicked_at"]),
        ]

    def __str__(self):
        return f"click {self.smart_link.slug} @ {self.clicked_at:%Y-%m-%d}"
