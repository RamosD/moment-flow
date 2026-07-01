"""Reusable DRF permission classes for multi-tenant, role-based access.

``IsWorkspaceMember`` (re-exported from the workspaces app) only checks active
membership. ``HasWorkspacePermission`` additionally checks that the member's role
grants the permission(s) the view requires for the current action.
"""

from rest_framework.permissions import BasePermission

# Re-exported so RBAC consumers have a single import location.
from apps.workspaces.permissions import (  # noqa: F401
    IsWorkspaceMember,
    resolve_active_workspace,
)

from .services import user_has_permission


def _required_permissions(view):
    """Resolve the permissions a view requires for the current action.

    Supports either a ``get_required_permissions()`` method or a
    ``required_permissions`` attribute (a list, or a dict keyed by action).
    """
    getter = getattr(view, "get_required_permissions", None)
    if callable(getter):
        return getter() or []
    declared = getattr(view, "required_permissions", None) or []
    if isinstance(declared, dict):
        return declared.get(getattr(view, "action", None), [])
    return declared


class HasWorkspacePermission(BasePermission):
    """Require active membership *and* the view's declared workspace permissions.

    The active workspace is resolved from the ``X-Workspace-ID`` header and
    attached to ``request.workspace``. Views declare the permissions they need
    via ``required_permissions`` (list or action-keyed dict) or
    ``get_required_permissions()``.
    """

    message = "You do not have permission to perform this action in this workspace."

    def has_permission(self, request, view):
        workspace = resolve_active_workspace(request)
        request.workspace = workspace

        required = _required_permissions(view)
        if not required:
            return True
        return all(
            user_has_permission(request.user, workspace, perm) for perm in required
        )
