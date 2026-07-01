"""Integrations bridge: references to technical jobs run by external services.

Django does *not* execute heavy logic (metrics, moments, insights, rendering) —
that belongs to FastAPI / the Content Renderer / workers. This app only keeps a
*reference* to such jobs so Django can track their state and associate them with
product entities. An external service updates the reference via the internal
callback endpoint.
"""

from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ExternalJobReference(BaseModel):
    """A pointer to a technical job executed by an external service."""

    class JobType(models.TextChoices):
        METRICS_COLLECTION = "metrics_collection", _("Metrics collection")
        MOMENT_DETECTION = "moment_detection", _("Moment detection")
        INSIGHT_GENERATION = "insight_generation", _("Insight generation")
        RECOMMENDATION_GENERATION = "recommendation_generation", _("Recommendation generation")
        CONTENT_GENERATION = "content_generation", _("Content generation")
        CONTENT_PREVIEW = "content_preview", _("Content preview")
        REPORT_GENERATION = "report_generation", _("Report generation")
        MEDIA_KIT_GENERATION = "media_kit_generation", _("Media kit generation")
        VIDEO_RENDERING = "video_rendering", _("Video rendering")

    class Provider(models.TextChoices):
        INTELLIGENCE_ENGINE = "intelligence_engine", _("Intelligence Engine")
        CONTENT_RENDERER = "content_renderer", _("Content Renderer")
        REPORT_RENDERER = "report_renderer", _("Report Renderer")
        VIDEO_RENDERER = "video_renderer", _("Video Renderer")
        # Kept for backward compatibility with rows created before the registry
        # aligned provider names; not produced by new code.
        FASTAPI_INTELLIGENCE = "fastapi_intelligence", _("FastAPI Intelligence")
        WORKER = "worker", _("Worker")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        SUBMITTED = "submitted", _("Submitted")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        PARTIALLY_COMPLETED = "partially_completed", _("Partially completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")
        TIMEOUT = "timeout", _("Timeout")

    # Terminal states cannot transition further via callback.
    TERMINAL_STATUSES = (
        Status.COMPLETED,
        Status.PARTIALLY_COMPLETED,
        Status.FAILED,
        Status.CANCELLED,
        Status.EXPIRED,
    )
    # States from which an explicit retry is allowed.
    RETRYABLE_STATUSES = (
        Status.FAILED,
        Status.TIMEOUT,
        Status.CANCELLED,
        Status.EXPIRED,
    )

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        verbose_name=_("workspace"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_jobs",
    )
    job_type = models.CharField(_("job type"), max_length=30, choices=JobType.choices)
    provider = models.CharField(
        _("provider"),
        max_length=30,
        choices=Provider.choices,
        default=Provider.WORKER,
    )
    external_job_id = models.CharField(_("external job id"), max_length=255, blank=True)
    related_entity_type = models.CharField(
        _("related entity type"), max_length=80, blank=True
    )
    related_entity_id = models.CharField(
        _("related entity id"), max_length=64, blank=True
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("requested by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_external_jobs",
    )
    requested_at = models.DateTimeField(_("requested at"), default=now)
    submitted_at = models.DateTimeField(_("submitted at"), null=True, blank=True)
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    failed_at = models.DateTimeField(_("failed at"), null=True, blank=True)
    callback_received_at = models.DateTimeField(
        _("callback received at"), null=True, blank=True
    )
    error_message = models.TextField(_("error message"), blank=True)
    # Tracing & idempotency.
    request_id = models.CharField(_("request id"), max_length=64, blank=True)
    idempotency_key = models.CharField(
        _("idempotency key"), max_length=255, blank=True
    )
    retry_count = models.PositiveIntegerField(_("retry count"), default=0)
    # Payloads (no secrets — the internal token only ever travels in headers).
    request_payload = models.JSONField(_("request payload"), default=dict, blank=True)
    response_payload = models.JSONField(_("response payload"), default=dict, blank=True)
    callback_payload = models.JSONField(_("callback payload"), default=dict, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("external job reference")
        verbose_name_plural = _("external job references")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_job_id"],
                condition=~models.Q(external_job_id=""),
                name="unique_provider_external_job_id",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["related_entity_type", "related_entity_id"]),
            # Fast lookup for submission idempotency.
            models.Index(fields=["idempotency_key", "status"]),
            models.Index(fields=["request_id"]),
        ]

    def __str__(self):
        return f"{self.job_type} ({self.status})"
