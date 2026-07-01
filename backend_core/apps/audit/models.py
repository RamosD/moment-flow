"""Audit model: an append-only record of critical actions.

An ``AuditEvent`` captures *who* did *what* to *which* entity, with optional
before/after snapshots. It is immutable: there is no ``updated_at`` and the admin
exposes it read-only. The actor's IP/user-agent are stored hashed only (never in
clear) — see ``apps.audit.utils``.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class AuditEvent(UUIDModel):
    """An immutable record of a critical, traceable action."""

    class ActorType(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")
        ADMIN = "admin", _("Admin")
        API_KEY = "api_key", _("API key")
        WORKER = "worker", _("Worker")

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        verbose_name=_("workspace"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("actor user"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_type = models.CharField(
        _("actor type"),
        max_length=20,
        choices=ActorType.choices,
        default=ActorType.SYSTEM,
    )
    action = models.CharField(_("action"), max_length=100)
    entity_type = models.CharField(_("entity type"), max_length=80, blank=True)
    entity_id = models.CharField(_("entity id"), max_length=64, blank=True)
    before_data = models.JSONField(_("before data"), default=dict, blank=True)
    after_data = models.JSONField(_("after data"), default=dict, blank=True)
    ip_address_hash = models.CharField(_("IP address hash"), max_length=64, blank=True)
    user_agent_hash = models.CharField(_("user agent hash"), max_length=64, blank=True)
    created_at = models.DateTimeField(
        _("created at"), auto_now_add=True, editable=False, db_index=True
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("audit event")
        verbose_name_plural = _("audit events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "action"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor_user"]),
        ]

    def __str__(self):
        return f"{self.action} ({self.actor_type})"
