"""Core API viewsets."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets

from apps.workspaces.permissions import WORKSPACE_ID_HEADER, IsWorkspaceMember

from .models import Asset
from .serializers import AssetSerializer


@extend_schema(
    parameters=[
        OpenApiParameter(
            name=WORKSPACE_ID_HEADER,
            location=OpenApiParameter.HEADER,
            required=True,
            type=str,
            description="UUID of the active workspace.",
        )
    ]
)
class AssetViewSet(viewsets.ModelViewSet):
    """CRUD for assets of the active workspace (resolved from X-Workspace-ID).

    Listing is strictly scoped to the active workspace, so assets never leak
    across tenants. Soft-deleted assets are excluded by the default manager.
    """

    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    lookup_field = "id"
    queryset = Asset.objects.none()
    filterset_fields = ["asset_type", "storage_provider"]
    search_fields = ["file_name", "storage_key"]
    ordering_fields = ["created_at", "file_size_bytes"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Asset.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Asset.objects.none()
        return Asset.objects.filter(workspace=workspace).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            workspace=self.request.workspace, created_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()
