"""Catalogue models: Artist, Track and TrackPlatformLink.

All entities are tenant-owned (workspace FK) and reuse the core abstract bases.
Slugs are unique per workspace. Deep platform validation / metrics are out of
scope here (they belong to FastAPI); Django only persists links and light metadata.
"""

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    BaseModel,
    CreatedUpdatedByModel,
    SoftDeleteModel,
    WorkspaceOwnedModel,
)


class Artist(BaseModel, SoftDeleteModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        ARCHIVED = "archived", _("Archived")

    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)
    country = models.CharField(_("country"), max_length=2, blank=True)
    market = models.CharField(_("market"), max_length=2, blank=True)
    primary_genre = models.CharField(_("primary genre"), max_length=80, blank=True)
    language = models.CharField(_("language"), max_length=10, blank=True)
    bio_short = models.CharField(_("short bio"), max_length=500, blank=True)
    bio_long = models.TextField(_("long bio"), blank=True)
    image_asset = models.ForeignKey(
        "core.Asset",
        verbose_name=_("image asset"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artist_images",
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("artist")
        verbose_name_plural = _("artists")
        ordering = ["-created_at"]
        base_manager_name = "all_objects"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_artist_slug_per_workspace",
            )
        ]
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self):
        return self.name


class Track(BaseModel, SoftDeleteModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    class TrackType(models.TextChoices):
        SINGLE = "single", _("Single")
        MUSIC_VIDEO = "music_video", _("Music video")
        ALBUM_TRACK = "album_track", _("Album track")
        REMIX = "remix", _("Remix")
        LIVE = "live", _("Live")
        FREESTYLE = "freestyle", _("Freestyle")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SCHEDULED = "scheduled", _("Scheduled")
        RELEASED = "released", _("Released")
        MONITORING = "monitoring", _("Monitoring")
        PAUSED = "paused", _("Paused")
        ARCHIVED = "archived", _("Archived")

    artist = models.ForeignKey(
        Artist,
        verbose_name=_("artist"),
        on_delete=models.CASCADE,
        related_name="tracks",
    )
    title = models.CharField(_("title"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255)
    release_date = models.DateField(_("release date"), null=True, blank=True)
    track_type = models.CharField(
        _("track type"),
        max_length=20,
        choices=TrackType.choices,
        default=TrackType.SINGLE,
    )
    primary_genre = models.CharField(_("primary genre"), max_length=80, blank=True)
    language = models.CharField(_("language"), max_length=10, blank=True)
    market = models.CharField(_("market"), max_length=2, blank=True)
    cover_asset = models.ForeignKey(
        "core.Asset",
        verbose_name=_("cover asset"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="track_covers",
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("track")
        verbose_name_plural = _("tracks")
        ordering = ["-created_at"]
        base_manager_name = "all_objects"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_track_slug_per_workspace",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["artist"]),
        ]

    def __str__(self):
        return self.title


class TrackPlatformLink(BaseModel, WorkspaceOwnedModel):
    """A track's reference on an external platform (e.g. a YouTube URL)."""

    class Platform(models.TextChoices):
        YOUTUBE = "youtube", _("YouTube")
        SPOTIFY = "spotify", _("Spotify")
        APPLE_MUSIC = "apple_music", _("Apple Music")
        DEEZER = "deezer", _("Deezer")
        SOUNDCLOUD = "soundcloud", _("SoundCloud")
        AUDIOMACK = "audiomack", _("Audiomack")
        BOOMPLAY = "boomplay", _("Boomplay")
        TIKTOK = "tiktok", _("TikTok")
        INSTAGRAM = "instagram", _("Instagram")
        FACEBOOK = "facebook", _("Facebook")
        CUSTOM = "custom", _("Custom")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        VALID = "valid", _("Valid")
        INVALID = "invalid", _("Invalid")
        PRIVATE = "private", _("Private")
        REMOVED = "removed", _("Removed")
        PAUSED = "paused", _("Paused")

    track = models.ForeignKey(
        Track,
        verbose_name=_("track"),
        on_delete=models.CASCADE,
        related_name="platform_links",
    )
    platform = models.CharField(_("platform"), max_length=20, choices=Platform.choices)
    external_id = models.CharField(_("external id"), max_length=255, blank=True)
    url = models.URLField(_("url"), max_length=1000)
    canonical_url = models.URLField(_("canonical url"), max_length=1000, blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.PENDING
    )
    last_validated_at = models.DateTimeField(_("last validated at"), null=True, blank=True)
    validation_error = models.CharField(_("validation error"), max_length=500, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("track platform link")
        verbose_name_plural = _("track platform links")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "platform", "external_id"],
                condition=~Q(external_id=""),
                name="unique_platform_external_id_per_workspace",
            )
        ]
        indexes = [models.Index(fields=["workspace", "platform"])]

    def __str__(self):
        return f"{self.platform}: {self.external_id or self.url}"
