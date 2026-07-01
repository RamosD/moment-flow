"""Public, workspace-scoped API for persistent campaign actions."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.rbac.viewsets import WorkspaceScopedRBACViewSet
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

from .filters import CampaignActionFilter
from .models import CampaignAction
from .serializers import CampaignActionSerializer, DismissCampaignActionSerializer
from .services import CampaignActionTransitionError, transition_campaign_action

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)

_CAMPAIGN_ACTION_PERMS = {
    "list": ["campaigns:view"],
    "retrieve": ["campaigns:view"],
    "create": ["campaigns:update"],
    "partial_update": ["campaigns:update"],
    "mark_reviewed": ["campaigns:update"],
    "dismiss": ["campaigns:update"],
    "cancel": ["campaigns:update"],
    "complete": ["campaigns:update"],
}


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM])
class CampaignActionViewSet(WorkspaceScopedRBACViewSet):
    """List, create, retrieve and partially update campaign actions."""

    serializer_class = CampaignActionSerializer
    model = CampaignAction
    queryset = CampaignAction.objects.none()
    filterset_class = CampaignActionFilter
    search_fields = ["title", "description", "recommendation_ref"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "status",
        "priority",
        "action_type",
    ]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]
    required_permissions = _CAMPAIGN_ACTION_PERMS

    def perform_create(self, serializer):
        serializer.save(
            workspace=self.request.workspace,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def _transition(self, request, target_status, *, dismiss_reason=""):
        campaign_action = self.get_object()
        try:
            campaign_action = transition_campaign_action(
                campaign_action,
                target_status,
                actor=request.user,
                dismiss_reason=dismiss_reason,
            )
        except CampaignActionTransitionError as exc:
            raise ValidationError({exc.field: [str(exc)]}) from exc
        return Response(self.get_serializer(campaign_action).data)

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=None,
        responses=CampaignActionSerializer,
        summary="Mark a campaign action as reviewed",
    )
    @action(detail=True, methods=["post"], url_path="mark-reviewed")
    def mark_reviewed(self, request, id=None):
        return self._transition(request, CampaignAction.Status.COMPLETED)

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=DismissCampaignActionSerializer,
        responses=CampaignActionSerializer,
        summary="Dismiss a campaign action with a reason",
    )
    @action(detail=True, methods=["post"])
    def dismiss(self, request, id=None):
        payload = DismissCampaignActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return self._transition(
            request,
            CampaignAction.Status.DISMISSED,
            dismiss_reason=payload.validated_data["dismiss_reason"],
        )

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=None,
        responses=CampaignActionSerializer,
        summary="Cancel a campaign action",
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, id=None):
        return self._transition(request, CampaignAction.Status.CANCELLED)

    @extend_schema(
        parameters=[_WORKSPACE_HEADER_PARAM],
        request=None,
        responses=CampaignActionSerializer,
        summary="Complete a campaign action",
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, id=None):
        return self._transition(request, CampaignAction.Status.COMPLETED)
