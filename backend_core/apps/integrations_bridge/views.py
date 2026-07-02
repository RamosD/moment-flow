"""Internal callback endpoint for external technical jobs.

Authenticated by the ``X-Internal-Token`` header (see ``IsInternalService``), not
by JWT. An external service (FastAPI/renderer/worker) calls this to report a
job's terminal/intermediate state. Django only updates the reference and routes
the callback to a per-type handler — it never runs the job itself.

Security & idempotency contract:
  - No / wrong / unconfigured token  → 403 (permission layer).
  - Invalid payload / missing workspace_id → 400.
  - Unknown job                      → 404.
  - workspace_id mismatch            → 400 (workspace_id is mandatory).
  - entity.type / entity.id mismatch → 400 (when provided).
  - Duplicate callback (same status) → 200, no repeated effects.
  - Terminal job, different status   → 409.
"""

import logging

from django.utils.timezone import now
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .callbacks import callback_dispatcher
from .health import check_dependencies, liveness_report, readiness_report
from .logging_utils import log_job_event
from .models import ExternalJobReference
from .permissions import INTERNAL_TOKEN_HEADER, IsInternalService
from .serializers import ExternalJobReferenceSerializer, JobCallbackSerializer

logger = logging.getLogger("integrations_bridge")

_INTERNAL_TOKEN_PARAM = OpenApiParameter(
    name=INTERNAL_TOKEN_HEADER,
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="Shared internal service token.",
)


@extend_schema(
    parameters=[_INTERNAL_TOKEN_PARAM],
    request=JobCallbackSerializer,
    responses={200: ExternalJobReferenceSerializer, 400: None, 403: None, 404: None, 409: None},
    summary="Internal callback to update an external job's state (token-protected)",
)
class ExternalJobCallbackView(APIView):
    """Update an ``ExternalJobReference`` from an authenticated internal caller."""

    permission_classes = [IsInternalService]
    authentication_classes = []

    def post(self, request):
        serializer = JobCallbackSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            # Never log the payload/token — only the rejection reason.
            logger.warning("event=callback_rejected reason=invalid_payload")
            raise
        data = serializer.validated_data

        job = self._resolve_job(data)
        log_job_event("callback_received", job)
        self._validate_compatibility(job, data)

        new_status = data["status"]

        # Idempotent: a repeated callback for the same state is a no-op.
        if job.status == new_status:
            log_job_event("callback_noop", job, reason="same_status")
            return Response(ExternalJobReferenceSerializer(job).data)

        # A terminal job never transitions to a different state.
        if job.status in ExternalJobReference.TERMINAL_STATUSES:
            log_job_event(
                "callback_rejected", job,
                level=logging.WARNING, reason="terminal_conflict", attempted=new_status,
            )
            return Response(
                {
                    "detail": (
                        f"Job is already in terminal state '{job.status}' and "
                        f"cannot transition to '{new_status}'."
                    )
                },
                status=409,
            )

        # Persist the callback before dispatch (recorded even for placeholders).
        job.callback_payload = request.data if isinstance(request.data, dict) else {}
        job.callback_received_at = now()
        job.save(update_fields=["callback_payload", "callback_received_at", "updated_at"])

        callback_dispatcher(
            job,
            status=new_status,
            result=data.get("result"),
            error=data.get("error"),
            error_message=self._error_message(data),
            metadata=data.get("metadata") or {},
        )
        job.refresh_from_db()
        log_job_event("callback_processed", job)
        return Response(ExternalJobReferenceSerializer(job).data)

    @staticmethod
    def _error_message(data) -> str:
        error = data.get("error")
        if isinstance(error, dict):
            return error.get("message", "") or data.get("error_message", "")
        return data.get("error_message", "")

    def _resolve_job(self, data):
        job_uuid = data.get("job_id") or data.get("job")
        if job_uuid:
            job = ExternalJobReference.objects.filter(id=job_uuid).first()
            if job is None:
                raise NotFound("Job reference not found.")
            return job

        qs = ExternalJobReference.objects.filter(
            external_job_id=data["external_job_id"]
        )
        provider = data.get("provider")
        if provider:
            qs = qs.filter(provider=provider)
        job = qs.order_by("-created_at").first()
        if job is None:
            raise NotFound("Job reference not found.")
        return job

    def _validate_compatibility(self, job, data):
        """Reject a callback whose workspace/entity contradicts the job.

        ``workspace_id`` is mandatory and must match the job's workspace. ``entity``
        is optional but, when present, ``type``/``id`` must match the job.
        """
        workspace_id = data.get("workspace_id")
        if str(workspace_id) != str(job.workspace_id):
            self._reject(job, "workspace_mismatch")
            raise ValidationError(
                {"workspace_id": "Does not match the job's workspace."}
            )

        entity = data.get("entity") or {}
        entity_type = entity.get("type")
        entity_id = entity.get("id")
        if (
            entity_type
            and job.related_entity_type
            and entity_type != job.related_entity_type
        ):
            self._reject(job, "entity_type_mismatch")
            raise ValidationError({"entity": "entity.type does not match the job."})
        if (
            entity_id
            and job.related_entity_id
            and str(entity_id) != str(job.related_entity_id)
        ):
            self._reject(job, "entity_id_mismatch")
            raise ValidationError({"entity": "entity.id does not match the job."})

    @staticmethod
    def _reject(job, reason):
        log_job_event("callback_rejected", job, level=logging.WARNING, reason=reason)


class SystemDependencyHealthView(APIView):
    """Aggregated health of the Backend Core's technical dependencies.

    Probes the Intelligence Engine and the Content Renderer (public ``/health``,
    no token sent) plus the database, and returns a normalized report.

    **Protected (staff only).** The response exposes operational detail about
    internal services, so it is gated behind ``IsAdminUser`` (OBS-STG-003 /
    OBS-PDEC-001 / OBS-RSK-005). It never exposes a token or a full URL (URLs are
    reduced to ``configured`` / ``not_configured``).

    Always returns **HTTP 200** with the per-dependency status in the body — a
    failing dependency yields ``degraded`` / ``unavailable`` for that entry and in
    the overall status, never an unexpected 500.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        summary="Aggregated health of the technical dependencies (staff only)",
        description=(
            "Returns the operational status of the Intelligence Engine, the "
            "Content Renderer and the database. Per-dependency status is one of "
            "ok | degraded | unavailable | misconfigured | unknown; the overall "
            "status is ok | degraded | unavailable. No token or full URL is "
            "exposed."
        ),
    )
    def get(self, request):
        return Response(check_dependencies())


class SystemLivenessView(APIView):
    """``GET /api/v1/system/health/live/`` — public liveness probe (STG-PRE-006).

    Mirrors the Intelligence Engine's and Content Renderer's own ``/health``:
    public, no dependency checks, just confirms the process can answer a
    request. Never confuse this with readiness (below) — a process can be
    alive while its database is unreachable.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        summary="Liveness probe (public, no dependency checks)",
        description="Always 200 while the process can serve requests at all.",
    )
    def get(self, request):
        return Response(liveness_report())


class SystemReadinessView(APIView):
    """``GET /api/v1/system/health/ready/`` — public readiness probe (STG-PRE-006).

    Checks only the database (see ``readiness_report``) — deliberately public
    and deliberately minimal, exposing just ``ok``/``unavailable`` and nothing
    about the Intelligence Engine or the Content Renderer (that operational
    detail stays behind the staff-only aggregated endpoint above). Returns
    HTTP 503 when not ready, so load balancers/orchestrators can act on it
    without authentication — matching the security posture of the
    Intelligence Engine's and Content Renderer's own public ``/health``.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT},
        summary="Readiness probe (public; database only)",
        description=(
            "200 when the database is reachable, 503 otherwise. Does not "
            "reflect the Intelligence Engine or the Content Renderer — see "
            "the staff-only aggregated endpoint for that."
        ),
    )
    def get(self, request):
        report = readiness_report()
        status_code = 200 if report["status"] == "ok" else 503
        return Response(report, status=status_code)
