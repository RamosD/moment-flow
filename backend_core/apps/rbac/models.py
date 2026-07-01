"""RBAC models: Role, Permission and the Role↔Permission link.

Roles can be global *system* roles (``workspace`` is null, ``is_system`` true) or
workspace-specific roles. A user's role in a workspace is carried by
``apps.workspaces.WorkspaceMember.role`` (FK to ``Role``).
"""

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Permission(BaseModel):
    """An atomic, named capability such as ``artists:create``."""

    key = models.CharField(_("key"), max_length=100, unique=True)
    name = models.CharField(_("name"), max_length=150)
    description = models.TextField(_("description"), blank=True)
    domain = models.CharField(_("domain"), max_length=50, blank=True)

    class Meta:
        verbose_name = _("permission")
        verbose_name_plural = _("permissions")
        ordering = ["key"]

    def __str__(self):
        return self.key


class Role(BaseModel):
    """A named set of permissions, scoped globally or to a single workspace."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="roles",
    )
    key = models.CharField(_("key"), max_length=50)
    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    is_system = models.BooleanField(_("system role"), default=False)
    permissions = models.ManyToManyField(
        Permission, through="RolePermission", related_name="roles", blank=True
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["key"],
                condition=Q(workspace__isnull=True),
                name="unique_system_role_key",
            ),
            models.UniqueConstraint(
                fields=["workspace", "key"],
                condition=Q(workspace__isnull=False),
                name="unique_workspace_role_key",
            ),
        ]

    def __str__(self):
        scope = "system" if self.workspace_id is None else str(self.workspace_id)
        return f"{self.key} ({scope})"


class RolePermission(BaseModel):
    """Through model linking a Role to a Permission."""

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="permission_roles"
    )

    class Meta:
        verbose_name = _("role permission")
        verbose_name_plural = _("role permissions")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="unique_role_permission"
            )
        ]

    def __str__(self):
        return f"{self.role.key} -> {self.permission.key}"
