"""Workspace and WorkspaceMember API viewsets."""

from django.utils.timezone import now
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.services import record_audit_event
from apps.rbac.models import Role
from apps.rbac.permissions import HasWorkspacePermission
from apps.rbac.services import require_workspace_permission

from .models import Workspace, WorkspaceMember
from .permissions import WORKSPACE_ID_HEADER, IsWorkspaceMember
from .serializers import WorkspaceMemberSerializer, WorkspaceSerializer
from .services import create_workspace

WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """CRUD for workspaces the authenticated user is an active member of.

    Listing is strictly scoped to the requester's active memberships. Mutating an
    existing workspace requires the ``workspace:manage`` permission in that
    workspace (checked against the object, not a header).
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    queryset = Workspace.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Workspace.objects.none()
        return (
            Workspace.objects.filter(
                members__user=self.request.user,
                members__status=WorkspaceMember.Status.ACTIVE,
            )
            .distinct()
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        # The creator becomes the active owner member (see services).
        serializer.instance = create_workspace(
            user=self.request.user, **serializer.validated_data
        )

    def perform_update(self, serializer):
        require_workspace_permission(
            self.request.user, serializer.instance, "workspace:manage"
        )
        serializer.save()

    def perform_destroy(self, instance):
        require_workspace_permission(self.request.user, instance, "workspace:manage")
        instance.soft_delete()

    @extend_schema(
        parameters=[WORKSPACE_HEADER_PARAM],
        responses=WorkspaceSerializer,
        summary="Resolve the active workspace from the X-Workspace-ID header",
    )
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated, IsWorkspaceMember],
    )
    def current(self, request):
        serializer = self.get_serializer(request.workspace)
        return Response(serializer.data)


@extend_schema(parameters=[WORKSPACE_HEADER_PARAM])
class WorkspaceMemberViewSet(viewsets.ModelViewSet):
    """Members of the active workspace (resolved from X-Workspace-ID).

    All actions operate within the header workspace where the requester is an
    active member. Writes are gated by RBAC: inviting needs ``members:invite``;
    changing or removing members needs ``members:manage``. Reads are open to any
    active member.
    """

    serializer_class = WorkspaceMemberSerializer
    permission_classes = [permissions.IsAuthenticated, HasWorkspacePermission]
    lookup_field = "id"
    queryset = WorkspaceMember.objects.none()

    required_permissions = {
        "create": ["members:invite"],
        "update": ["members:manage"],
        "partial_update": ["members:manage"],
        "destroy": ["members:manage"],
    }

    def get_required_permissions(self):
        return self.required_permissions.get(self.action, [])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WorkspaceMember.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return WorkspaceMember.objects.none()
        return WorkspaceMember.objects.filter(workspace=workspace).order_by(
            "-created_at"
        )

    def _resolve_role(self, workspace, role_key):
        """Prefer a workspace-specific role, then a system role, for ``role_key``."""
        return (
            Role.objects.filter(workspace=workspace, key=role_key).first()
            or Role.objects.filter(workspace__isnull=True, key=role_key).first()
        )

    def perform_create(self, serializer):
        workspace = self.request.workspace
        role_key = serializer.validated_data.get("role_key") or "viewer"
        role = self._resolve_role(workspace, role_key)
        if role is None:
            raise ValidationError({"role_key": f"Unknown role '{role_key}'."})
        status = serializer.validated_data.get("status", WorkspaceMember.Status.ACTIVE)
        joined_at = now() if status == WorkspaceMember.Status.ACTIVE else None
        member = serializer.save(
            workspace=workspace,
            role=role,
            role_key=role_key,
            invited_by=self.request.user,
            joined_at=joined_at,
        )
        record_audit_event(
            action="member.added",
            workspace=workspace,
            actor_user=self.request.user,
            entity_type="workspace_member",
            entity_id=member.id,
            after_data={"user": str(member.user_id), "role_key": member.role_key},
            request=self.request,
        )

    def perform_update(self, serializer):
        workspace = self.request.workspace
        old_role_key = serializer.instance.role_key
        role_key = serializer.validated_data.get("role_key")
        extra = {}
        if role_key:
            role = self._resolve_role(workspace, role_key)
            if role is None:
                raise ValidationError({"role_key": f"Unknown role '{role_key}'."})
            extra["role"] = role
        member = serializer.save(**extra)
        if role_key and role_key != old_role_key:
            record_audit_event(
                action="member.role_changed",
                workspace=workspace,
                actor_user=self.request.user,
                entity_type="workspace_member",
                entity_id=member.id,
                before_data={"role_key": old_role_key},
                after_data={"role_key": member.role_key},
                request=self.request,
            )
