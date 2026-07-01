"""Multi-tenancy helpers: resolve the active workspace from X-Workspace-ID.

The active workspace is carried by the ``X-Workspace-ID`` request header. A
request is only allowed to act on a workspace where the authenticated user is an
*active* member. There is no implicit "global" workspace.
"""

import uuid

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission

from .models import Workspace, WorkspaceMember

WORKSPACE_ID_HEADER = "X-Workspace-ID"


def resolve_active_workspace(request) -> Workspace:
    """Return the workspace referenced by X-Workspace-ID for this user.

    Raises ``ValidationError`` (400) when the header is missing or malformed, and
    ``PermissionDenied`` (403) when the workspace does not exist or the user is
    not an active member (the two cases are not distinguished, to avoid leaking
    workspace existence).
    """
    raw = request.headers.get(WORKSPACE_ID_HEADER)
    if not raw:
        raise ValidationError({WORKSPACE_ID_HEADER: "This header is required."})

    try:
        workspace_id = uuid.UUID(str(raw))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError({WORKSPACE_ID_HEADER: "Must be a valid UUID."}) from exc

    workspace = Workspace.objects.filter(pk=workspace_id).first()
    if workspace is None:
        raise PermissionDenied("Workspace not found or access denied.")

    is_member = WorkspaceMember.objects.filter(
        workspace=workspace,
        user=request.user,
        status=WorkspaceMember.Status.ACTIVE,
    ).exists()
    if not is_member:
        raise PermissionDenied("You are not an active member of this workspace.")

    return workspace


def get_current_workspace(request):
    """Convenience accessor that caches the resolved workspace on the request."""
    workspace = getattr(request, "workspace", None)
    if workspace is None:
        workspace = resolve_active_workspace(request)
        request.workspace = workspace
    return workspace


class IsWorkspaceMember(BasePermission):
    """Allow access only to active members of the X-Workspace-ID workspace.

    On success the resolved workspace is attached as ``request.workspace`` for
    downstream use by views and querysets.
    """

    def has_permission(self, request, view):
        request.workspace = resolve_active_workspace(request)
        return True
