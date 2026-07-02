"""Base utility models shared across domain apps.

These are infrastructure mixins, not business models. Concrete domain models
inherit from them. ``Asset`` is the one concrete model here: a generic reference
to a stored file (logo, cover, output, PDF, …) owned by a workspace.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Abstract base that adds self-managed ``created_at`` / ``updated_at``."""

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet with soft-delete aware helpers."""

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Soft-delete every row in the queryset."""
        return self.update(deleted_at=now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Default manager that hides soft-deleted rows."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """Abstract base adding ``deleted_at`` and soft-delete semantics.

    ``objects`` excludes soft-deleted rows by default; ``all_objects`` returns
    everything. ``base_manager_name`` points at ``all_objects`` so related
    lookups (e.g. reverse FKs) are never silently truncated.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"

    def soft_delete(self):
        self.deleted_at = now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class UUIDModel(models.Model):
    """Abstract base that uses a non-sequential UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """Convenience base combining a UUID primary key and timestamps."""

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class WorkspaceOwnedModel(models.Model):
    """Abstract base for tenant-owned entities (mandatory ``workspace`` FK)."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True


class CreatedUpdatedByModel(models.Model):
    """Abstract base tracking which users created/updated the row."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class CorrelationIdModel(models.Model):
    """Abstract base adding an optional end-to-end ``correlation_id`` (STG-PRE-005).

    Set from the HTTP request that created the row (see
    ``apps.core.middleware.CorrelationIdMiddleware``) so the same id can be
    traced across the Backend Core, the Intelligence Engine and the Content
    Renderer via structured logs. It **complements** domain ids (action id,
    report id, job id, campaign id) — it never replaces or substitutes them.
    Blank when the row was created outside a request context (e.g. a
    management command or a test that does not set it explicitly).
    """

    correlation_id = models.CharField(
        _("correlation id"), max_length=64, blank=True, db_index=True
    )

    class Meta:
        abstract = True


class Asset(BaseModel, SoftDeleteModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    """Generic reference to a stored file owned by a workspace.

    The storage backend is recorded but no real upload happens here — this is a
    metadata/contract entity. Storage stays local/placeholder for now.
    """

    class AssetType(models.TextChoices):
        ARTIST_PHOTO = "artist_photo", _("Artist photo")
        COVER = "cover", _("Cover")
        LOGO = "logo", _("Logo")
        TEMPLATE_ASSET = "template_asset", _("Template asset")
        REPORT_PDF = "report_pdf", _("Report PDF")
        MEDIA_KIT_ASSET = "media_kit_asset", _("Media kit asset")
        UPLOADED_IMAGE = "uploaded_image", _("Uploaded image")
        GENERATED_OUTPUT = "generated_output", _("Generated output")
        AUDIO_PREVIEW = "audio_preview", _("Audio preview")
        OTHER = "other", _("Other")

    class StorageProvider(models.TextChoices):
        LOCAL = "local", _("Local")
        S3 = "s3", _("Amazon S3")
        R2 = "r2", _("Cloudflare R2")
        GCS = "gcs", _("Google Cloud Storage")

    asset_type = models.CharField(
        _("asset type"),
        max_length=30,
        choices=AssetType.choices,
        default=AssetType.OTHER,
    )
    storage_provider = models.CharField(
        _("storage provider"),
        max_length=20,
        choices=StorageProvider.choices,
        default=StorageProvider.LOCAL,
    )
    bucket = models.CharField(_("bucket"), max_length=255, blank=True)
    storage_key = models.CharField(_("storage key"), max_length=1024, blank=True)
    file_name = models.CharField(_("file name"), max_length=255, blank=True)
    mime_type = models.CharField(_("MIME type"), max_length=120, blank=True)
    file_size_bytes = models.BigIntegerField(_("file size (bytes)"), null=True, blank=True)
    width = models.PositiveIntegerField(_("width"), null=True, blank=True)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True)
    duration_seconds = models.FloatField(_("duration (s)"), null=True, blank=True)
    checksum = models.CharField(_("checksum"), max_length=128, blank=True)
    # Canonical URL where the file can be fetched (public URL today; may become a
    # signed URL once a private-bucket provider is chosen — see STG-PRE-003).
    # Long max_length because signed URLs carry query-string signatures.
    public_url = models.URLField(_("public URL"), max_length=2048, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("asset")
        verbose_name_plural = _("assets")
        ordering = ["-created_at"]
        base_manager_name = "all_objects"
        indexes = [
            models.Index(fields=["workspace", "asset_type"]),
        ]

    def __str__(self):
        return f"{self.asset_type}: {self.file_name or self.storage_key or self.pk}"
