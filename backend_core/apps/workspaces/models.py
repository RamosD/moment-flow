"""Workspace (tenant) and WorkspaceMember models.

Every client-owned entity in ChartRex belongs to a workspace. A user may belong
to several workspaces; membership is modelled by ``WorkspaceMember``.

RBAC is not implemented yet, so ``WorkspaceMember.role`` is a temporary free-text
field. It will be replaced by a FK to ``apps.rbac.Role`` in a later phase.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, SoftDeleteModel

# Temporary textual roles (until apps.rbac exists).
ROLE_OWNER = "owner"


class Workspace(BaseModel, SoftDeleteModel):
    """A tenant. Soft-deletable; identified by a unique slug."""

    class WorkspaceType(models.TextChoices):
        ARTIST = "artist", _("Artist")
        MANAGER = "manager", _("Manager")
        LABEL = "label", _("Label")
        DISTRIBUTOR = "distributor", _("Distributor")
        AGENCY = "agency", _("Agency")
        MEDIA = "media", _("Media")
        WHITE_LABEL = "white_label", _("White label")
        INTERNAL = "internal", _("Internal")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        TRIAL = "trial", _("Trial")
        SUSPENDED = "suspended", _("Suspended")
        CANCELLED = "cancelled", _("Cancelled")
        ARCHIVED = "archived", _("Archived")

    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255, unique=True)
    workspace_type = models.CharField(
        _("workspace type"),
        max_length=20,
        choices=WorkspaceType.choices,
        default=WorkspaceType.ARTIST,
    )
    country = models.CharField(_("country"), max_length=2, blank=True)
    market = models.CharField(_("market"), max_length=2, blank=True)
    default_language = models.CharField(_("default language"), max_length=10, default="en")
    timezone = models.CharField(_("timezone"), max_length=64, default="UTC")
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.TRIAL
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_workspaces",
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("workspace")
        verbose_name_plural = _("workspaces")
        ordering = ["-created_at"]
        base_manager_name = "all_objects"

    def __str__(self):
        return self.name


class WorkspaceMember(BaseModel):
    """Association between a user and a workspace.

    Uniqueness is enforced on ``(workspace, user)``: a user cannot be added to
    the same workspace twice.
    """

    class Status(models.TextChoices):
        INVITED = "invited", _("Invited")
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        REMOVED = "removed", _("Removed")

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    # FK to the RBAC role (system or workspace-specific).
    role = models.ForeignKey(
        "rbac.Role",
        verbose_name=_("role"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    # Denormalized role key kept for compatibility and quick lookups.
    role_key = models.CharField(_("role key"), max_length=50, default="viewer", blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_workspace_invitations",
    )
    joined_at = models.DateTimeField(_("joined at"), null=True, blank=True)

    class Meta:
        verbose_name = _("workspace member")
        verbose_name_plural = _("workspace members")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"], name="unique_workspace_member"
            )
        ]

    def __str__(self):
        return f"{self.user} @ {self.workspace} ({self.role_key})"
