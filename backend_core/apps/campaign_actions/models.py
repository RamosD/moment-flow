"""Persistent campaign-action records.

A CampaignAction tracks an operational decision made from a transient
recommendation. It belongs to one campaign/workspace and may point to an
existing content or reporting artefact without replacing that artefact.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, CreatedUpdatedByModel, WorkspaceOwnedModel


class CampaignAction(BaseModel, WorkspaceOwnedModel, CreatedUpdatedByModel):
    """A persistent, workspace-scoped action associated with a campaign."""

    class ActionType(models.TextChoices):
        CONTENT_PACK = "content_pack", _("Content pack")
        REPORT_REQUEST = "report_request", _("Report request")
        MEDIA_KIT_REQUEST = "media_kit_request", _("Media kit request")
        MANUAL_TASK = "manual_task", _("Manual task")
        MARK_REVIEWED = "mark_reviewed", _("Mark reviewed")
        DISMISS = "dismiss", _("Dismiss")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        DISMISSED = "dismissed", _("Dismissed")
        CANCELLED = "cancelled", _("Cancelled")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        URGENT = "urgent", _("Urgent")

    class Source(models.TextChoices):
        RECOMMENDATION = "recommendation", _("Recommendation")
        MANUAL = "manual", _("Manual")

    campaign = models.ForeignKey(
        "campaigns.Campaign",
        verbose_name=_("campaign"),
        on_delete=models.CASCADE,
        related_name="campaign_actions",
    )
    recommendation_ref = models.CharField(
        _("recommendation reference"), max_length=512, blank=True, default=""
    )
    recommendation_snapshot = models.JSONField(
        _("recommendation snapshot"), default=dict, blank=True
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    action_type = models.CharField(
        _("action type"),
        max_length=30,
        choices=ActionType.choices,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    priority = models.CharField(
        _("priority"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    source = models.CharField(
        _("source"),
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    dismiss_reason = models.TextField(_("dismiss reason"), blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    related_content_pack_request = models.ForeignKey(
        "content.ContentPackRequest",
        verbose_name=_("related content pack request"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_actions",
    )
    related_content_output = models.ForeignKey(
        "content.ContentOutput",
        verbose_name=_("related content output"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_actions",
    )
    related_report = models.ForeignKey(
        "reports.Report",
        verbose_name=_("related report"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_actions",
    )
    related_media_kit = models.ForeignKey(
        "reports.MediaKit",
        verbose_name=_("related media kit"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_actions",
    )

    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)

    class Meta:
        verbose_name = _("campaign action")
        verbose_name_plural = _("campaign actions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "campaign"], name="ca_ws_campaign_idx"),
            models.Index(
                fields=["workspace", "campaign", "recommendation_ref"],
                name="ca_ws_campaign_ref_idx",
            ),
            models.Index(fields=["status"], name="ca_status_idx"),
            models.Index(fields=["action_type"], name="ca_action_type_idx"),
            models.Index(fields=["created_at"], name="ca_created_at_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "workspace",
                    "campaign",
                    "recommendation_ref",
                    "action_type",
                ],
                condition=(
                    ~models.Q(recommendation_ref="")
                    & models.Q(status__in=("pending", "in_progress", "completed"))
                ),
                name="unique_active_campaign_action",
            )
        ]

    def __str__(self):
        return self.title

