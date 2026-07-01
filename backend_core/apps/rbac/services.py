"""RBAC service helpers used by views, permissions and other apps."""

from rest_framework.exceptions import PermissionDenied

from apps.workspaces.models import WorkspaceMember

from .models import Role


def get_user_workspace_role(user, workspace):
    """Return the active ``Role`` of ``user`` in ``workspace`` (or ``None``).

    Prefers the FK on the membership; falls back to resolving a system role by
    the denormalized ``role_key`` for robustness.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    member = (
        WorkspaceMember.objects.filter(
            workspace=workspace,
            user=user,
            status=WorkspaceMember.Status.ACTIVE,
        )
        .select_related("role")
        .first()
    )
    if member is None:
        return None
    if member.role_id:
        return member.role
    if member.role_key:
        return Role.objects.filter(
            workspace__isnull=True, key=member.role_key
        ).first()
    return None


def user_has_permission(user, workspace, permission_key) -> bool:
    """True if ``user`` holds ``permission_key`` via their role in ``workspace``."""
    role = get_user_workspace_role(user, workspace)
    if role is None:
        return False
    return role.permissions.filter(key=permission_key).exists()


def require_workspace_permission(user, workspace, permission_key) -> None:
    """Raise ``PermissionDenied`` unless the user holds the permission."""
    if not user_has_permission(user, workspace, permission_key):
        raise PermissionDenied(
            f"Missing permission '{permission_key}' for this workspace."
        )
