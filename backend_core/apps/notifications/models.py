"""Notification model: internal, in-app notifications scoped to a workspace.

A notification belongs to a workspace and is either directed at a specific user
or broadcast to the whole workspace (``user`` is null). No email is sent and no
digest is built here — only the in-app entity and its read state.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, WorkspaceOwnedModel


class Notification(BaseModel, WorkspaceOwnedModel):
    """An in-app notification for a user (or a workspace-wide broadcast)."""

    class NotificationType(models.TextChoices):
        REPORT_READY = "report_ready", _("Report ready")
        MEDIA_KIT_READY = "media_kit_ready", _("Media kit ready")
        CONTENT_READY = "content_ready", _("Content ready")
        CAMPAIGN_UPDATE = "campaign_update", _("Campaign update")
        MEMBER_ADDED = "member_added", _("Member added")
        BILLING_ALERT = "billing_alert", _("Billing alert")
        QUOTA_ALERT = "quota_alert", _("Quota alert")
        SYSTEM = "system", _("System")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        UNREAD = "unread", _("Unread")
        READ = "read", _("Read")
        DISMISSED = "dismissed", _("Dismissed")
        ARCHIVED = "archived", _("Archived")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(
        _("notification type"),
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(_("title"), max_length=255)
    message = models.TextField(_("message"), blank=True)
    related_entity_type = models.CharField(
        _("related entity type"), max_length=80, blank=True
    )
    related_entity_id = models.CharField(
        _("related entity id"), max_length=64, blank=True
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.UNREAD
    )
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "user"]),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"
