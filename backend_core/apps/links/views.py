"""Smart link viewsets, the stats action and the public resolution endpoint."""

import uuid

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.billing.models import UsageEvent
from apps.billing.services import check_workspace_limit, record_creation_usage
from apps.content.models import ContentOutput
from apps.rbac.viewsets import WorkspaceScopedRBACViewSet
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

from .filters import (
    SmartLinkClickFilter,
    SmartLinkDestinationFilter,
    SmartLinkFilter,
)
from .models import SmartLink, SmartLinkClick, SmartLinkDestination
from .serializers import (
    PublicSmartLinkSerializer,
    SmartLinkClickSerializer,
    SmartLinkDestinationSerializer,
    SmartLinkSerializer,
)
from .services import generate_unique_slug
from .utils import ip_hash, parse_device_and_browser, user_agent, user_agent_hash

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)

_LINK_PERMS = {
    "list": ["links:view"],
    "retrieve": ["links:view"],
    "create": ["links:create"],
    "update": ["links:update"],
    "partial_update": ["links:update"],
    "destroy": ["links:delete"],
    "stats": ["links:view"],
}


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class SmartLinkViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = SmartLinkSerializer
    model = SmartLink
    queryset = SmartLink.objects.none()
    filterset_class = SmartLinkFilter
    search_fields = ["slug", "title"]
    ordering_fields = ["created_at", "title", "status"]
    required_permissions = _LINK_PERMS

    def perform_create(self, serializer):
        workspace = self.request.workspace
        # Quota: block when the plan's smart_links_limit would be exceeded.
        check_workspace_limit(workspace, "smart_links_limit")
        title = serializer.validated_data.get("title") or "link"
        link = serializer.save(
            workspace=workspace,
            slug=generate_unique_slug(SmartLink, title),
            created_by=self.request.user,
        )
        record_creation_usage(
            workspace, UsageEvent.EventType.SMART_LINK_CREATED, "smart_link", link.id
        )
        record_audit_event(
            action="smart_link.created",
            workspace=workspace,
            actor_user=self.request.user,
            entity_type="smart_link",
            entity_id=link.id,
            after_data={"slug": link.slug, "title": link.title},
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        responses={200: None},
        summary="Basic click statistics for a smart link",
    )
    @action(detail=True, methods=["get"])
    def stats(self, request, id=None):
        link = self.get_object()
        clicks = SmartLinkClick.objects.filter(smart_link=link)
        by_destination = [
            {"destination": str(row["destination"]) if row["destination"] else None,
             "count": row["count"]}
            for row in clicks.values("destination").annotate(count=Count("id"))
        ]
        by_day = [
            {"day": row["day"].isoformat() if row["day"] else None, "count": row["count"]}
            for row in (
                clicks.annotate(day=TruncDate("clicked_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            )
        ]
        return Response(
            {
                "smart_link": str(link.id),
                "total_clicks": clicks.count(),
                "by_destination": by_destination,
                "by_day": by_day,
            }
        )


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class SmartLinkDestinationViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = SmartLinkDestinationSerializer
    model = SmartLinkDestination
    queryset = SmartLinkDestination.objects.none()
    filterset_class = SmartLinkDestinationFilter
    ordering_fields = ["sort_order", "created_at"]
    required_permissions = _LINK_PERMS

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class SmartLinkClickViewSet(WorkspaceScopedRBACViewSet):
    """Read-only access to recorded clicks (created by the public endpoint)."""

    serializer_class = SmartLinkClickSerializer
    model = SmartLinkClick
    queryset = SmartLinkClick.objects.none()
    filterset_class = SmartLinkClickFilter
    ordering_fields = ["clicked_at"]
    http_method_names = ["get", "head", "options"]
    required_permissions = {
        "list": ["links:view"],
        "retrieve": ["links:view"],
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SmartLinkClick.objects.none()
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return SmartLinkClick.objects.none()
        return SmartLinkClick.objects.filter(workspace=workspace).order_by("-clicked_at")


@extend_schema(
    parameters=[
        OpenApiParameter("destination", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("platform", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("content_output", str, OpenApiParameter.QUERY, required=False),
    ],
    responses={200: PublicSmartLinkSerializer, 302: None, 404: None},
    summary="Public smart link resolution (records a click; redirects or lists destinations)",
)
class PublicSmartLinkView(APIView):
    """Public (unauthenticated) smart link resolution + click tracking.

    - Only ``active`` links resolve; otherwise 404 (paused/expired never redirect).
    - With an explicit ``destination=<id>`` or ``platform=<key>``, a click is
      recorded and the response is a 302 redirect to that destination.
    - Without an explicit choice, a click is recorded (destination null) and the
      payload of active destinations is returned (no arbitrary auto-redirect).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = PublicSmartLinkSerializer

    def get(self, request, slug):
        link = (
            SmartLink.objects.filter(slug=slug, status=SmartLink.Status.ACTIVE)
            .select_related("campaign", "track")
            .first()
        )
        if link is None:
            raise Http404("Smart link not available.")

        destination = self._resolve_destination(request, link)
        self._record_click(request, link, destination)

        if destination is not None:
            return HttpResponseRedirect(destination.url)
        return Response(PublicSmartLinkSerializer(link).data)

    def _resolve_destination(self, request, link):
        destination_id = request.query_params.get("destination")
        platform = request.query_params.get("platform")
        active = link.destinations.filter(is_active=True)

        if destination_id:
            try:
                uuid.UUID(str(destination_id))
            except (ValueError, TypeError) as exc:
                raise Http404("Invalid destination.") from exc
            destination = active.filter(id=destination_id).first()
            if destination is None:
                raise Http404("Destination not available.")
            return destination

        if platform:
            return active.filter(platform=platform).order_by("sort_order").first()

        return None

    def _resolve_content_output(self, request, link):
        raw = request.query_params.get("content_output") or request.query_params.get(
            "utm_content"
        )
        if not raw:
            return None
        try:
            output_id = uuid.UUID(str(raw))
        except (ValueError, TypeError):
            return None
        return ContentOutput.objects.filter(
            id=output_id, workspace=link.workspace
        ).first()

    def _record_click(self, request, link, destination):
        ua = user_agent(request)
        device_type, browser = parse_device_and_browser(ua)
        params = request.query_params
        return SmartLinkClick.objects.create(
            workspace=link.workspace,
            smart_link=link,
            destination=destination,
            content_output=self._resolve_content_output(request, link),
            campaign=link.campaign,
            track=link.track,
            referrer=request.META.get("HTTP_REFERER", "")[:1000],
            utm_source=params.get("utm_source", "")[:255],
            utm_medium=params.get("utm_medium", "")[:255],
            utm_campaign=params.get("utm_campaign", "")[:255],
            utm_content=params.get("utm_content", "")[:255],
            device_type=device_type,
            browser=browser,
            ip_hash=ip_hash(request),
            user_agent_hash=user_agent_hash(request),
        )
