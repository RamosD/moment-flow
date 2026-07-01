"""Catalogue viewsets: tenant-scoped and RBAC-gated."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets

from apps.audit.services import record_audit_event
from apps.billing.models import UsageEvent
from apps.billing.services import check_workspace_limit, record_creation_usage
from apps.rbac.permissions import HasWorkspacePermission
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

from .filters import ArtistFilter, TrackFilter, TrackPlatformLinkFilter
from .models import Artist, Track, TrackPlatformLink
from .serializers import (
    ArtistSerializer,
    TrackPlatformLinkSerializer,
    TrackSerializer,
)
from .services import generate_unique_slug

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)


class WorkspaceScopedRBACMixin:
    """Shared behaviour: resolve the active workspace and gate by RBAC.

    Subclasses set ``model`` and ``required_permissions`` (action -> [perm keys]).
    The active workspace is provided by ``HasWorkspacePermission`` as
    ``request.workspace``.
    """

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


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class ArtistViewSet(WorkspaceScopedRBACMixin, viewsets.ModelViewSet):
    serializer_class = ArtistSerializer
    model = Artist
    queryset = Artist.objects.none()
    filterset_class = ArtistFilter
    search_fields = ["name", "slug", "primary_genre"]
    ordering_fields = ["created_at", "name", "status"]
    required_permissions = {
        "list": ["artists:view"],
        "retrieve": ["artists:view"],
        "create": ["artists:create"],
        "update": ["artists:update"],
        "partial_update": ["artists:update"],
        "destroy": ["artists:delete"],
    }

    def perform_create(self, serializer):
        workspace = self.request.workspace
        # Quota: block when the plan's artists_limit would be exceeded.
        check_workspace_limit(workspace, "artists_limit")
        artist = serializer.save(
            workspace=workspace,
            slug=generate_unique_slug(Artist, workspace, serializer.validated_data["name"]),
            created_by=self.request.user,
        )
        record_creation_usage(
            workspace, UsageEvent.EventType.ARTIST_CREATED, "artist", artist.id
        )
        record_audit_event(
            action="artist.created",
            workspace=workspace,
            actor_user=self.request.user,
            entity_type="artist",
            entity_id=artist.id,
            after_data={"name": artist.name},
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class TrackViewSet(WorkspaceScopedRBACMixin, viewsets.ModelViewSet):
    serializer_class = TrackSerializer
    model = Track
    queryset = Track.objects.none()
    filterset_class = TrackFilter
    search_fields = ["title", "slug", "primary_genre"]
    ordering_fields = ["created_at", "title", "release_date", "status"]
    required_permissions = {
        "list": ["tracks:view"],
        "retrieve": ["tracks:view"],
        "create": ["tracks:create"],
        "update": ["tracks:update"],
        "partial_update": ["tracks:update"],
        "destroy": ["tracks:delete"],
    }

    def perform_create(self, serializer):
        workspace = self.request.workspace
        # Quota: block when the plan's tracks_limit would be exceeded.
        check_workspace_limit(workspace, "tracks_limit")
        track = serializer.save(
            workspace=workspace,
            slug=generate_unique_slug(Track, workspace, serializer.validated_data["title"]),
            created_by=self.request.user,
        )
        record_creation_usage(
            workspace, UsageEvent.EventType.TRACK_CREATED, "track", track.id
        )
        record_audit_event(
            action="track.created",
            workspace=workspace,
            actor_user=self.request.user,
            entity_type="track",
            entity_id=track.id,
            after_data={"title": track.title, "artist": str(track.artist_id)},
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class TrackPlatformLinkViewSet(WorkspaceScopedRBACMixin, viewsets.ModelViewSet):
    serializer_class = TrackPlatformLinkSerializer
    model = TrackPlatformLink
    queryset = TrackPlatformLink.objects.none()
    filterset_class = TrackPlatformLinkFilter
    search_fields = ["external_id", "url"]
    ordering_fields = ["created_at", "platform", "status"]
    # Platform links are part of the track catalogue, so reuse tracks:* perms.
    required_permissions = {
        "list": ["tracks:view"],
        "retrieve": ["tracks:view"],
        "create": ["tracks:create"],
        "update": ["tracks:update"],
        "partial_update": ["tracks:update"],
        "destroy": ["tracks:delete"],
    }

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)
