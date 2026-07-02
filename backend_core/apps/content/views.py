"""Content viewsets.

Templates and packs are a read-only catalogue (global + workspace) gated by
``content:view``. Requests and outputs are workspace-owned and writable, gated by
``content:generate`` / ``content:export``. No rendering happens here.
"""

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.rbac.permissions import HasWorkspacePermission
from apps.rbac.viewsets import WorkspaceScopedRBACViewSet
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

from .filters import (
    ContentOutputFilter,
    ContentPackFilter,
    ContentPackRequestFilter,
    TemplateFilter,
)
from .models import (
    ContentOutput,
    ContentPack,
    ContentPackRequest,
    ContentPackTemplate,
    Template,
    TemplateVersion,
)
from .serializers import (
    ContentOutputSerializer,
    ContentPackRequestSerializer,
    ContentPackSerializer,
    ContentPackTemplateSerializer,
    TemplateSerializer,
    TemplateVersionSerializer,
)
from .services import create_content_pack_request

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class GlobalOrWorkspaceReadViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalogue: rows that are global or owned by the active workspace.

    ``workspace_field`` is the lookup path to the owning workspace (e.g.
    ``"workspace"`` or ``"template__workspace"``).
    """

    permission_classes = [permissions.IsAuthenticated, HasWorkspacePermission]
    lookup_field = "id"
    model = None
    workspace_field = "workspace"
    required_permissions = {"list": ["content:view"], "retrieve": ["content:view"]}

    def get_required_permissions(self):
        return self.required_permissions.get(self.action, [])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return self.model.objects.none()
        field = self.workspace_field
        return self.model.objects.filter(
            Q(**{f"{field}__isnull": True}) | Q(**{field: workspace})
        )


class TemplateViewSet(GlobalOrWorkspaceReadViewSet):
    serializer_class = TemplateSerializer
    model = Template
    workspace_field = "workspace"
    queryset = Template.objects.none()
    filterset_class = TemplateFilter
    search_fields = ["template_key", "name"]
    ordering_fields = ["name", "created_at"]


class TemplateVersionViewSet(GlobalOrWorkspaceReadViewSet):
    serializer_class = TemplateVersionSerializer
    model = TemplateVersion
    workspace_field = "template__workspace"
    queryset = TemplateVersion.objects.none()
    filterset_fields = ["template", "renderer_type", "status"]
    ordering_fields = ["created_at", "version"]


class ContentPackViewSet(GlobalOrWorkspaceReadViewSet):
    serializer_class = ContentPackSerializer
    model = ContentPack
    workspace_field = "workspace"
    queryset = ContentPack.objects.none()
    filterset_class = ContentPackFilter
    search_fields = ["pack_key", "name"]
    ordering_fields = ["name", "created_at"]


class ContentPackTemplateViewSet(GlobalOrWorkspaceReadViewSet):
    serializer_class = ContentPackTemplateSerializer
    model = ContentPackTemplate
    workspace_field = "content_pack__workspace"
    queryset = ContentPackTemplate.objects.none()
    filterset_fields = ["content_pack", "template", "required"]
    ordering_fields = ["sort_order", "created_at"]

    def get_queryset(self):
        # Ordered by the pack's declared sort order.
        return super().get_queryset().order_by("sort_order", "created_at")


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class ContentPackRequestViewSet(WorkspaceScopedRBACViewSet):
    """Create/list content pack requests (created in ``queued`` via the service)."""

    serializer_class = ContentPackRequestSerializer
    model = ContentPackRequest
    queryset = ContentPackRequest.objects.none()
    filterset_class = ContentPackRequestFilter
    ordering_fields = ["created_at", "status"]
    http_method_names = ["get", "post", "head", "options"]
    required_permissions = {
        "list": ["content:view"],
        "retrieve": ["content:view"],
        "create": ["content:generate"],
    }

    def perform_create(self, serializer):
        serializer.instance = create_content_pack_request(
            workspace=self.request.workspace,
            requested_by=self.request.user,
            correlation_id=getattr(self.request, "correlation_id", ""),
            **serializer.validated_data,
        )


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class ContentOutputViewSet(WorkspaceScopedRBACViewSet):
    """Content outputs as a core entity (placeholder; not rendered here)."""

    serializer_class = ContentOutputSerializer
    model = ContentOutput
    queryset = ContentOutput.objects.none()
    filterset_class = ContentOutputFilter
    search_fields = ["title", "output_type"]
    ordering_fields = ["created_at", "status"]
    http_method_names = ["get", "post", "patch", "head", "options"]
    required_permissions = {
        "list": ["content:view"],
        "retrieve": ["content:view"],
        "create": ["content:generate"],
        "partial_update": ["content:generate"],
        "export": ["content:export"],
    }

    def perform_create(self, serializer):
        serializer.save(
            workspace=self.request.workspace, created_by=self.request.user
        )

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        responses={200: None},
        summary="Export an output (placeholder — no real rendering)",
    )
    @action(detail=True, methods=["post"])
    def export(self, request, id=None):
        output = self.get_object()
        # Placeholder: real export/rendering is delegated to the Content Renderer.
        return Response(
            {
                "id": str(output.id),
                "status": output.status,
                "export": "placeholder",
                "detail": "Export is handled by the Content Renderer (not implemented here).",
            }
        )
