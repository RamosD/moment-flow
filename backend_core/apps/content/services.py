"""Service functions for the content domain.

A request is created in the ``queued`` state; the Content Renderer later produces
outputs via the internal callback. ``create_content_pack_request`` is that seam:
after the request is durably created (with billing), it opens a
``content_generation`` ``ExternalJobReference`` and submits it (or simulates it
under dry-run / stays queued when external jobs are disabled). No rendering and no
real asset creation happen here.

Billing integration: creating a request enforces the ``content_packs_per_month``
quota, records an idempotent ``content_pack_requested`` usage event, and — when
the pack declares a ``credit_cost`` in its metadata — reserves the credits up
front (raising a clear 402 if the balance is too low). Packs with no declared
cost skip the credit step (documented partial integration).
"""

import logging
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.billing.models import UsageEvent
from apps.billing.services import (
    check_workspace_limit,
    record_usage_event,
    reserve_credits,
)

from .models import ContentPack, ContentPackRequest
from .payloads import build_content_generation_payload

logger = logging.getLogger("content.services")


def _pack_credit_cost(content_pack) -> Decimal:
    """Return the credit cost declared on the pack metadata (0 when absent)."""
    raw = (content_pack.metadata or {}).get("credit_cost", 0) or 0
    try:
        return Decimal(str(raw))
    except (TypeError, ValueError):
        return Decimal("0")


def create_content_pack_request(
    *, workspace, requested_by, campaign, content_pack, track=None, artist=None,
    metadata=None, correlation_id="",
) -> ContentPackRequest:
    """Validate inputs, enforce billing, create a request (``queued``) and submit
    a ``content_generation`` external job.

    Validations:
      - ``campaign`` (and ``track``/``artist`` when provided) belong to ``workspace``;
      - ``content_pack`` is active and global or owned by ``workspace``;
      - the ``content_packs_per_month`` plan quota is not exceeded;
      - when the pack declares ``metadata.credit_cost`` > 0, the workspace has
        enough credits (reserved up front).

    The request + billing are created atomically (a failed credit reservation
    rolls them back, never charging twice on retry). The external job is created
    and submitted **after** that commit, so the request is never lost if the
    submission fails — the failure is recorded on the job and on the request
    metadata, and remains traceable. Rendering and asset creation are *not* done
    here (deferred to the renderer + a later callback phase).
    """
    if campaign.workspace_id != workspace.id:
        raise ValidationError({"campaign": "Campaign must belong to the active workspace."})
    if track is not None and track.workspace_id != workspace.id:
        raise ValidationError({"track": "Track must belong to the active workspace."})
    if artist is not None and artist.workspace_id != workspace.id:
        raise ValidationError({"artist": "Artist must belong to the active workspace."})

    if content_pack.workspace_id not in (None, workspace.id):
        raise ValidationError({"content_pack": "Pack is not available in this workspace."})
    if content_pack.status != ContentPack.Status.ACTIVE:
        raise ValidationError({"content_pack": "Pack is not active."})

    # Quota: monthly content-pack request limit (fails open without a plan).
    check_workspace_limit(workspace, "content_packs_per_month")

    credit_cost = _pack_credit_cost(content_pack)

    # --- Atomic: request + usage + credit reservation + "requested" audit. --- #
    with transaction.atomic():
        request = ContentPackRequest.objects.create(
            workspace=workspace,
            campaign=campaign,
            track=track,
            artist=artist,
            content_pack=content_pack,
            requested_by=requested_by,
            status=ContentPackRequest.Status.QUEUED,
            metadata=metadata or {},
            correlation_id=correlation_id,
        )
        logger.info(
            "event=content_pack_request_created content_pack_request_id=%s "
            "workspace_id=%s correlation_id=%s",
            request.id, workspace.id, correlation_id,
        )

        event, _ = record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.CONTENT_PACK_REQUESTED,
            related_entity_type="content_pack_request",
            related_entity_id=str(request.id),
            cost_units=credit_cost,
            idempotency_key=f"content_pack_requested:{request.id}",
        )
        request.usage_event_id = event.id

        # Reserve credits up front when the pack has a cost. Raises 402 (rolled
        # back) when the balance is insufficient, so we never queue an unpayable
        # request.
        if credit_cost > 0:
            reserve_credits(
                workspace,
                credit_cost,
                reason=f"content_pack:{content_pack.pack_key}",
                related_entity_type="content_pack_request",
                related_entity_id=str(request.id),
                idempotency_key=f"content_pack_reserve:{request.id}",
            )

        request.save(update_fields=["usage_event_id"])

        from apps.audit.services import record_audit_event

        record_audit_event(
            action="content_pack.requested",
            workspace=workspace,
            actor_user=requested_by,
            entity_type="content_pack_request",
            entity_id=request.id,
            after_data={
                "content_pack": content_pack.pack_key,
                "campaign": str(campaign.id),
            },
        )

    # --- Outside the transaction: open & submit the renderer job. --- #
    _submit_content_generation_job(request, requested_by, correlation_id)
    return request


def _submit_content_generation_job(request, requested_by, correlation_id="") -> None:
    """Create and submit the ``content_generation`` job for a request.

    Best-effort and non-fatal: ``create_and_submit_external_job`` already records
    submission failures on the job (``failed``/``timeout``) without raising, but
    any unexpected error here is caught, recorded on the request metadata and
    audited — the request itself is never lost.
    """
    from apps.audit.services import record_audit_event
    from apps.integrations_bridge.models import ExternalJobReference
    from apps.integrations_bridge.services import create_and_submit_external_job

    try:
        payload = build_content_generation_payload(request)
        job, _created = create_and_submit_external_job(
            workspace=request.workspace,
            job_type=ExternalJobReference.JobType.CONTENT_GENERATION,
            related_entity_type="content_pack_request",
            related_entity_id=str(request.id),
            requested_by=requested_by,
            payload=payload,
            idempotency_key=f"content_generation:{request.id}",
            metadata={"content_pack_request_id": str(request.id)},
            request_id=correlation_id or None,
        )
    except Exception as exc:  # noqa: BLE001 — never lose the request over submission
        logger.warning(
            "content_generation submission error request_id=%s: %s", request.id, exc
        )
        request.metadata = {
            **(request.metadata or {}),
            "job_submission_error": str(exc),
        }
        request.save(update_fields=["metadata", "updated_at"])
        return

    # A synchronous submission failure (renderer unreachable) may already have
    # updated this same row's status/metadata in the database (see
    # ``integrations_bridge.services._propagate_submission_failure``) — refresh
    # before merging so that write is never clobbered by this stale copy.
    request.refresh_from_db()
    # Link request <-> job and audit the submission.
    request.metadata = {**(request.metadata or {}), "external_job_id": str(job.id)}
    request.save(update_fields=["metadata", "updated_at"])

    record_audit_event(
        action="content_pack.job_submitted",
        workspace=request.workspace,
        actor_user=requested_by,
        entity_type="content_pack_request",
        entity_id=request.id,
        after_data={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "provider": job.provider,
            "status": job.status,
        },
    )
