"""Reports and media-kit viewsets: tenant-scoped and RBAC-gated.

Reads need ``reports:view``; creating/updating needs ``reports:generate``. No
rendering happens here — entities are created in a non-terminal state and a
``storage_asset`` is attached later by an external worker. Creating a report or a
media kit records a billing usage event (when billing is installed).
"""

import logging

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.rbac.viewsets import WorkspaceScopedRBACViewSet
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

logger = logging.getLogger("reports.views")

from .filters import (
    MediaKitFilter,
    MediaKitItemFilter,
    ReportFilter,
    ReportSectionFilter,
)
from .models import MediaKit, MediaKitItem, Report, ReportSection
from .serializers import (
    MediaKitItemSerializer,
    MediaKitSerializer,
    ReportSectionSerializer,
    ReportSerializer,
)
from .services import (
    submit_media_kit_generation_job,
    submit_report_generation_job,
)

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)

# Reports and media kits share the reports:* permission set.
_REPORT_PERMS = {
    "list": ["reports:view"],
    "retrieve": ["reports:view"],
    "create": ["reports:generate"],
    "update": ["reports:generate"],
    "partial_update": ["reports:generate"],
    "destroy": ["reports:generate"],
}


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class ReportViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = ReportSerializer
    model = Report
    queryset = Report.objects.none()
    filterset_class = ReportFilter
    search_fields = ["title", "report_type"]
    ordering_fields = ["created_at", "status", "report_type", "period_start"]
    # No hard delete: a report is archived via its status.
    http_method_names = ["get", "post", "patch", "head", "options"]
    required_permissions = _REPORT_PERMS

    def perform_create(self, serializer):
        workspace = self.request.workspace
        correlation_id = getattr(self.request, "correlation_id", "")
        # Quota: monthly report limit (fails open without a plan).
        from apps.billing.services import check_workspace_limit

        check_workspace_limit(workspace, "reports_per_month")
        report = serializer.save(
            workspace=workspace,
            requested_by=self.request.user,
            correlation_id=correlation_id,
        )
        logger.info(
            "event=report_created report_id=%s workspace_id=%s correlation_id=%s",
            report.id, workspace.id, correlation_id,
        )
        # Records the report_generated usage event and submits the renderer job.
        submit_report_generation_job(
            report, requested_by=self.request.user, correlation_id=correlation_id
        )


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class ReportSectionViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = ReportSectionSerializer
    model = ReportSection
    queryset = ReportSection.objects.none()
    filterset_class = ReportSectionFilter
    ordering_fields = ["sort_order", "created_at"]
    required_permissions = _REPORT_PERMS

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReportSection.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return ReportSection.objects.none()
        return ReportSection.objects.filter(workspace=workspace).order_by(
            "sort_order", "created_at"
        )

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class MediaKitViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = MediaKitSerializer
    model = MediaKit
    queryset = MediaKit.objects.none()
    filterset_class = MediaKitFilter
    search_fields = ["title"]
    ordering_fields = ["created_at", "status", "title"]
    http_method_names = ["get", "post", "patch", "head", "options"]
    required_permissions = _REPORT_PERMS

    def perform_create(self, serializer):
        correlation_id = getattr(self.request, "correlation_id", "")
        media_kit = serializer.save(
            workspace=self.request.workspace,
            created_by=self.request.user,
            correlation_id=correlation_id,
        )
        logger.info(
            "event=media_kit_created media_kit_id=%s workspace_id=%s correlation_id=%s",
            media_kit.id, self.request.workspace.id, correlation_id,
        )
        # Records the media_kit_generated usage event and submits the renderer job.
        submit_media_kit_generation_job(
            media_kit, requested_by=self.request.user, correlation_id=correlation_id
        )


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class MediaKitItemViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = MediaKitItemSerializer
    model = MediaKitItem
    queryset = MediaKitItem.objects.none()
    filterset_class = MediaKitItemFilter
    ordering_fields = ["sort_order", "created_at"]
    required_permissions = _REPORT_PERMS

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MediaKitItem.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return MediaKitItem.objects.none()
        return MediaKitItem.objects.filter(workspace=workspace).order_by(
            "sort_order", "created_at"
        )

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)
