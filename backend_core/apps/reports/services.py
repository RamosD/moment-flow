"""Service helpers for the reports/media-kit domain.

Two responsibilities:
  1. Billing hook — record a usage event when a report/media kit is created (the
     import is guarded so the app never hard-fails if billing is absent).
  2. External job submission — open and submit a ``report_generation`` /
     ``media_kit_generation`` ``ExternalJobReference`` (dry-run friendly, idempotent,
     resilient). Real PDF/ZIP/media-kit rendering is the renderer's job; the
     completed/failed callback is implemented in a later phase.
"""

import logging

logger = logging.getLogger("reports.services")

REPORT_GENERATED = "report_generated"
MEDIA_KIT_GENERATED = "media_kit_generated"


def _record_usage(workspace, event_type, entity_type, entity_id):
    """Record a creation usage event when billing is installed (best effort)."""
    try:
        from apps.billing.services import record_creation_usage
    except ImportError:
        return None
    return record_creation_usage(workspace, event_type, entity_type, entity_id)


def record_report_created(report):
    """Record a ``report_generated`` usage event for a freshly created report."""
    return _record_usage(report.workspace, REPORT_GENERATED, "report", report.id)


def record_media_kit_created(media_kit):
    """Record a ``media_kit_generated`` usage event for a new media kit."""
    return _record_usage(
        media_kit.workspace, MEDIA_KIT_GENERATED, "media_kit", media_kit.id
    )


# --------------------------------------------------------------------------- #
# External job submission
# --------------------------------------------------------------------------- #
def submit_report_generation_job(report, *, requested_by=None, correlation_id=""):
    """Record usage and submit a ``report_generation`` job for the report."""
    from apps.integrations_bridge.models import ExternalJobReference

    from .payloads import build_report_generation_payload

    record_report_created(report)
    return _submit_external_job(
        report,
        job_type=ExternalJobReference.JobType.REPORT_GENERATION,
        entity_type="report",
        payload=build_report_generation_payload(report),
        idempotency_key=f"report_generation:{report.id}",
        requested_by=requested_by,
        audit_action="report.job_submitted",
        correlation_id=correlation_id,
    )


def submit_media_kit_generation_job(media_kit, *, requested_by=None, correlation_id=""):
    """Record usage and submit a ``media_kit_generation`` job for the media kit."""
    from apps.integrations_bridge.models import ExternalJobReference

    from .payloads import build_media_kit_generation_payload

    record_media_kit_created(media_kit)
    return _submit_external_job(
        media_kit,
        job_type=ExternalJobReference.JobType.MEDIA_KIT_GENERATION,
        entity_type="media_kit",
        payload=build_media_kit_generation_payload(media_kit),
        idempotency_key=f"media_kit_generation:{media_kit.id}",
        requested_by=requested_by,
        audit_action="media_kit.job_submitted",
        correlation_id=correlation_id,
    )


def _submit_external_job(
    entity, *, job_type, entity_type, payload, idempotency_key, requested_by, audit_action,
    correlation_id="",
):
    """Create & submit the external job; link it back; audit. Never raises.

    ``create_and_submit_external_job`` already records submission failures on the
    job (``failed``/``timeout``) without raising; any unexpected error is caught,
    recorded on the entity metadata and left traceable — the entity is never lost.

    ``correlation_id``, when provided (from the HTTP request that created
    ``entity`` — STG-PRE-005), becomes the job's own ``request_id`` so the same
    id ties the entity, the job and the Content Renderer's logs together.
    """
    from apps.integrations_bridge.services import create_and_submit_external_job

    try:
        job, _created = create_and_submit_external_job(
            workspace=entity.workspace,
            job_type=job_type,
            related_entity_type=entity_type,
            related_entity_id=str(entity.id),
            requested_by=requested_by,
            payload=payload,
            idempotency_key=idempotency_key,
            metadata={f"{entity_type}_id": str(entity.id)},
            request_id=correlation_id or None,
        )
    except Exception as exc:  # noqa: BLE001 — never lose the entity over submission
        logger.warning("%s submission error id=%s: %s", job_type, entity.id, exc)
        entity.metadata = {
            **(entity.metadata or {}),
            "job_submission_error": str(exc),
        }
        entity.save(update_fields=["metadata", "updated_at"])
        return None

    # A synchronous submission failure (renderer unreachable) may already have
    # updated this same row's status/metadata in the database (see
    # ``integrations_bridge.services._propagate_submission_failure``) — refresh
    # before merging so that write is never clobbered by this stale copy.
    entity.refresh_from_db()
    entity.metadata = {**(entity.metadata or {}), "external_job_id": str(job.id)}
    entity.save(update_fields=["metadata", "updated_at"])
    _audit_submission(entity, entity_type, audit_action, job, requested_by)
    return job


def _audit_submission(entity, entity_type, action, job, requested_by):
    try:
        from apps.audit.services import record_audit_event
    except ImportError:
        return
    record_audit_event(
        action=action,
        workspace=entity.workspace,
        actor_user=requested_by,
        actor_type=None if requested_by else "system",
        entity_type=entity_type,
        entity_id=entity.id,
        after_data={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "provider": job.provider,
            "status": job.status,
        },
    )
