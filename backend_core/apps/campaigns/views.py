"""Campaign viewsets: tenant-scoped and RBAC-gated."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

from apps.audit.services import record_audit_event
from apps.billing.models import UsageEvent
from apps.billing.services import check_workspace_limit, record_creation_usage
from apps.rbac.viewsets import WorkspaceScopedRBACViewSet
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

from .filters import CampaignFilter, CampaignGoalFilter, CampaignTrackFilter
from .intelligence_service import (
    CampaignNotFoundError,
    IntelligenceDisabledError,
    IntelligenceUnavailableError,
    IntelligenceUpstreamError,
    get_campaign_intelligence,
)
from .models import Campaign, CampaignGoal, CampaignTrack
from .serializers import (
    CampaignGoalSerializer,
    CampaignIntelligenceResponseSerializer,
    CampaignSerializer,
    CampaignTrackSerializer,
)
from .services import generate_unique_slug


class IntelligenceUnavailable(APIException):
    """503 — the engine is disabled or temporarily unavailable (retryable)."""

    status_code = 503
    default_detail = "Campaign intelligence is temporarily unavailable. Try again later."
    default_code = "intelligence_unavailable"


class IntelligenceUpstreamFailure(APIException):
    """502 — the engine returned an error we cannot expose as a client error."""

    status_code = 502
    default_detail = "Campaign intelligence could not be retrieved from the engine."
    default_code = "intelligence_upstream_error"

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)

_CAMPAIGN_PERMS = {
    "list": ["campaigns:view"],
    "retrieve": ["campaigns:view"],
    "create": ["campaigns:create"],
    "update": ["campaigns:update"],
    "partial_update": ["campaigns:update"],
    "destroy": ["campaigns:delete"],
    # Intelligence is read-only enrichment of a campaign → gated by view access.
    "intelligence": ["campaigns:view"],
}


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class CampaignViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = CampaignSerializer
    model = Campaign
    queryset = Campaign.objects.none()
    filterset_class = CampaignFilter
    search_fields = ["name", "slug", "primary_goal"]
    ordering_fields = ["created_at", "name", "start_date", "status"]
    required_permissions = _CAMPAIGN_PERMS

    def perform_create(self, serializer):
        workspace = self.request.workspace
        # Quota: block when the plan's campaigns_limit would be exceeded.
        check_workspace_limit(workspace, "campaigns_limit")
        campaign = serializer.save(
            workspace=workspace,
            slug=generate_unique_slug(Campaign, workspace, serializer.validated_data["name"]),
            created_by=self.request.user,
        )
        record_creation_usage(
            workspace, UsageEvent.EventType.CAMPAIGN_CREATED, "campaign", campaign.id
        )
        record_audit_event(
            action="campaign.created",
            workspace=workspace,
            actor_user=self.request.user,
            entity_type="campaign",
            entity_id=campaign.id,
            after_data={"name": campaign.name},
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=None,
        responses={200: CampaignIntelligenceResponseSerializer},
        summary="Synchronous campaign intelligence",
        description=(
            "Builds the campaign data bundle and calls the Intelligence Engine "
            "synchronously, returning analysis, scores, grade, moments, "
            "recommendations and summary. Read-only enrichment (no persistence)."
        ),
    )
    @action(detail=True, methods=["post"], url_path="intelligence")
    def intelligence(self, request, id=None):
        # get_object() is scoped to the active workspace by the base viewset, so a
        # campaign from another workspace (or a soft-deleted one) is a 404 here.
        campaign = self.get_object()
        try:
            outcome = get_campaign_intelligence(
                workspace=request.workspace,
                campaign=campaign,
                requested_by=request.user,
                request_id=getattr(request, "correlation_id", None),
            )
        except CampaignNotFoundError as exc:  # defensive (get_object already 404s)
            raise NotFound("Campaign not found in this workspace.") from exc
        except IntelligenceDisabledError as exc:
            raise IntelligenceUnavailable(
                "Campaign intelligence is disabled.", code="intelligence_disabled"
            ) from exc
        except IntelligenceUnavailableError as exc:
            raise IntelligenceUnavailable() from exc
        except IntelligenceUpstreamError as exc:
            raise IntelligenceUpstreamFailure() from exc
        return Response(outcome.as_dict())


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class CampaignTrackViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = CampaignTrackSerializer
    model = CampaignTrack
    queryset = CampaignTrack.objects.none()
    filterset_class = CampaignTrackFilter
    ordering_fields = ["created_at", "role"]
    required_permissions = _CAMPAIGN_PERMS

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class CampaignGoalViewSet(WorkspaceScopedRBACViewSet):
    serializer_class = CampaignGoalSerializer
    model = CampaignGoal
    queryset = CampaignGoal.objects.none()
    filterset_class = CampaignGoalFilter
    ordering_fields = ["created_at", "deadline", "status", "goal_type"]
    required_permissions = _CAMPAIGN_PERMS

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)
