"""Billing API.

Public catalogue (plans) is read-only. Workspace billing reads (active
subscription, period usage, credit balance) are gated by ``billing:view`` and
scoped to the active workspace from ``X-Workspace-ID``. The Stripe webhook is an
unauthenticated endpoint protected by signature verification (when configured).
"""

import json

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import HasWorkspacePermission
from apps.workspaces.permissions import WORKSPACE_ID_HEADER

from . import services
from .models import CreditLedgerEntry, Plan
from .serializers import (
    CreditLedgerEntrySerializer,
    PlanSerializer,
    SubscriptionSerializer,
)
from .webhooks import (
    SignatureVerificationError,
    log_and_process_event,
    verify_stripe_signature,
)

_WORKSPACE_HEADER_PARAM = OpenApiParameter(
    name=WORKSPACE_ID_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="UUID of the active workspace.",
)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only catalogue of public, active plans (no workspace context)."""

    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    queryset = Plan.objects.none()
    search_fields = ["plan_key", "name"]
    ordering_fields = ["base_price", "name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Plan.objects.none()
        return (
            Plan.objects.filter(is_public=True, status=Plan.Status.ACTIVE)
            .prefetch_related("features")
            .order_by("base_price", "name")
        )


class _WorkspaceBillingView(APIView):
    """Base for workspace-scoped billing reads gated by ``billing:view``."""

    permission_classes = [permissions.IsAuthenticated, HasWorkspacePermission]
    required_permissions = ["billing:view"]

    def get_required_permissions(self):
        return self.required_permissions


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM], responses=SubscriptionSerializer)
class ActiveSubscriptionView(_WorkspaceBillingView):
    """Return the active subscription of the workspace (or ``null``)."""

    def get(self, request):
        subscription = services.get_active_subscription(request.workspace)
        if subscription is None:
            return Response({"subscription": None})
        return Response(SubscriptionSerializer(subscription).data)


@extend_schema(
    parameters=[
        _WORKSPACE_HEADER_PARAM,
        OpenApiParameter("period", str, OpenApiParameter.QUERY, required=False,
                         description="Billing period bucket, e.g. 2026-06."),
    ],
    responses={200: None},
)
class PeriodUsageView(_WorkspaceBillingView):
    """Return aggregated usage for the workspace in a billing period."""

    def get(self, request):
        period = request.query_params.get("period") or services.current_billing_period()
        usage = services.get_period_usage(request.workspace, billing_period=period)
        return Response({"billing_period": period, "usage": usage})


@extend_schema(parameters=[_WORKSPACE_HEADER_PARAM], responses={200: None})
class CreditBalanceView(_WorkspaceBillingView):
    """Return the current credit balance and the most recent ledger entries."""

    def get(self, request):
        balance = services.get_credit_balance(request.workspace)
        recent = CreditLedgerEntry.objects.filter(
            workspace=request.workspace
        ).order_by("-created_at")[:20]
        return Response(
            {
                "balance": str(balance),
                "recent_entries": CreditLedgerEntrySerializer(recent, many=True).data,
            }
        )


@extend_schema(
    request=None,
    responses={200: None, 400: None},
    summary="Stripe webhook (skeleton; signature-verified when configured)",
)
class StripeWebhookView(APIView):
    """Receive Stripe webhooks, verify (when configured), store and process.

    - Verifies the ``Stripe-Signature`` header when ``STRIPE_WEBHOOK_SECRET`` is
      set; rejects invalid signatures with 400.
    - When the secret is not configured, accepts and stores the event but flags
      ``signature_verified: false`` (documented limitation).
    - Deduplicates on the Stripe event id so retries are not reprocessed.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.body
        secret = settings.STRIPE_WEBHOOK_SECRET
        signature_verified = False

        if secret:
            sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
            try:
                if not verify_stripe_signature(payload, sig_header, secret):
                    raise ValidationError({"detail": "Invalid Stripe signature."})
            except SignatureVerificationError as exc:
                raise ValidationError({"detail": str(exc)}) from exc
            signature_verified = True

        try:
            event = json.loads(payload.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValidationError({"detail": "Invalid JSON payload."}) from exc

        provider_event_id = event.get("id")
        if not provider_event_id:
            raise ValidationError({"detail": "Missing event id."})

        webhook_event, created = log_and_process_event(
            provider_event_id=provider_event_id,
            event_type=event.get("type"),
            payload=event,
            signature_verified=signature_verified,
        )
        return Response(
            {
                "received": True,
                "duplicate": not created,
                "status": webhook_event.status,
                "signature_verified": signature_verified,
            }
        )
