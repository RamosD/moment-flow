"""Reusable base viewset for tenant-scoped, RBAC-gated resources.

Resolves the active workspace from ``X-Workspace-ID`` (via
``HasWorkspacePermission``), scopes the queryset to it, and gates each action by
the permissions declared in ``required_permissions`` (an action -> [perm keys]
mapping). Subclasses set ``model`` and add ``perform_*`` as needed.
"""

from rest_framework import permissions, viewsets

from .permissions import HasWorkspacePermission


class WorkspaceScopedRBACViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasWorkspacePermission]
    lookup_field = "id"
    model = None
    required_permissions = {}

    def get_required_permissions(self):
        return self.required_permissions.get(self.action, [])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return self.model.objects.none()
        return self.model.objects.filter(workspace=workspace).order_by("-created_at")
