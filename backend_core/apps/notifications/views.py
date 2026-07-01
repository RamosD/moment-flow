"""Notification viewset: list a member's notifications and mark them read.

Notifications are created by the system (see ``services.create_notification``),
so the API is read-only plus two state-changing actions. Access is limited to
active members of the workspace resolved from ``X-Workspace-ID``; a user sees
notifications addressed to them and workspace-wide broadcasts (``user`` null).
"""

from django.db.models import Q
from django.utils.timezone import now
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workspaces.permissions import WORKSPACE_ID_HEADER, IsWorkspaceMember

from .filters import NotificationFilter
from .models import Notification
from .serializers import NotificationSerializer

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """List/retrieve notifications and mark them as read."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    lookup_field = "id"
    queryset = Notification.objects.none()
    filterset_class = NotificationFilter
    ordering_fields = ["created_at", "status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Notification.objects.none()
        # User-directed notifications plus workspace-wide broadcasts.
        return (
            Notification.objects.filter(workspace=workspace)
            .filter(Q(user=self.request.user) | Q(user__isnull=True))
            .order_by("-created_at")
        )

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=None,
        responses=NotificationSerializer,
        summary="Mark a notification as read",
    )
    @action(detail=True, methods=["post"])
    def read(self, request, id=None):
        notification = self.get_object()
        if notification.status != Notification.Status.READ:
            notification.status = Notification.Status.READ
            notification.read_at = now()
            notification.save(update_fields=["status", "read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=None,
        responses={200: None},
        summary="Mark all unread notifications as read",
    )
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(
            status=Notification.Status.UNREAD
        ).update(status=Notification.Status.READ, read_at=now())
        return Response({"updated": updated})
