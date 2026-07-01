"""Services for the integrations bridge.

Django *orchestrates* technical jobs; it never executes them. The entry point is
``create_and_submit_external_job``: it records an :class:`ExternalJobReference`
**before** any external call, then submits the job to the resolved service (or
simulates it under dry-run, or stays queued when external jobs are disabled).

Idempotency: a non-terminal job with the same ``idempotency_key`` is reused
instead of creating a duplicate. An explicit ``retry_external_job`` creates a new
job (with ``retry_count`` incremented) only from a retryable terminal state —
never overwriting the old job.

No secret ever leaves this module in a payload: the internal token only travels
in request *headers* (see :mod:`apps.integrations_bridge.clients`).
"""

import logging
import uuid

from django.utils.timezone import now

from . import registry
from .clients import (
    InternalClientError,
    InternalClientTimeout,
    InternalServiceClient,
)
from .logging_utils import log_job_event
from .models import ExternalJobReference

PAYLOAD_VERSION = "1.0"
# Conventional submission path on every external service. The job envelope
# carries job_type so the service can route internally.
SUBMIT_PATH = "/jobs/"


# --------------------------------------------------------------------------- #
# Backwards-compatible low-level helper (kept for existing callers/tests)
# --------------------------------------------------------------------------- #
def create_external_job_reference(
    *,
    job_type,
    provider=ExternalJobReference.Provider.WORKER,
    workspace=None,
    requested_by=None,
    external_job_id="",
    related_entity_type="",
    related_entity_id="",
    metadata=None,
) -> ExternalJobReference:
    """Create a queued reference to an external technical job (no submission)."""
    return ExternalJobReference.objects.create(
        job_type=job_type,
        provider=provider,
        workspace=workspace,
        requested_by=requested_by,
        external_job_id=external_job_id,
        related_entity_type=related_entity_type,
        related_entity_id=str(related_entity_id) if related_entity_id else "",
        status=ExternalJobReference.Status.QUEUED,
        metadata=metadata or {},
    )


# --------------------------------------------------------------------------- #
# Idempotency helpers
# --------------------------------------------------------------------------- #
def default_idempotency_key(job_type, related_entity_id) -> str:
    """Derive ``"<job_type>:<entity_id>"`` (stable per entity + job type)."""
    return f"{job_type}:{related_entity_id}" if related_entity_id else job_type


def find_active_job(*, workspace, idempotency_key):
    """Return a non-terminal job for ``(workspace, idempotency_key)`` or ``None``."""
    if not idempotency_key:
        return None
    return (
        ExternalJobReference.objects.filter(
            workspace=workspace, idempotency_key=idempotency_key
        )
        .exclude(status__in=ExternalJobReference.TERMINAL_STATUSES)
        .order_by("-created_at")
        .first()
    )


# --------------------------------------------------------------------------- #
# Payload envelope
# --------------------------------------------------------------------------- #
def build_request_envelope(job, payload) -> dict:
    """Wrap the caller payload in the versioned external-request envelope.

    Contains no secrets — only ids, the public callback URL and the domain
    payload. ``callback_url`` lets the service report back.
    """
    return {
        "job_id": str(job.id),
        "workspace_id": str(job.workspace_id) if job.workspace_id else None,
        "request_id": job.request_id,
        "job_type": job.job_type,
        "callback_url": registry.callback_url(),
        "entity": {
            "type": job.related_entity_type,
            "id": job.related_entity_id,
        },
        "payload_version": PAYLOAD_VERSION,
        "payload": payload or {},
    }


# --------------------------------------------------------------------------- #
# Create & submit
# --------------------------------------------------------------------------- #
def create_and_submit_external_job(
    *,
    workspace,
    job_type,
    related_entity_type,
    related_entity_id,
    requested_by=None,
    provider=None,
    payload=None,
    idempotency_key=None,
    metadata=None,
    retry_count=0,
):
    """Create an ExternalJobReference and submit it (or simulate / stay queued).

    Returns ``(job, created)``. ``created=False`` means an existing non-terminal
    job was reused (idempotency). The job is always persisted *before* any
    external call, so a submission failure never loses the reference.

    Behaviour by configuration:
      - ``EXTERNAL_JOBS_ENABLED=False`` → job stays ``queued`` (no call).
      - ``EXTERNAL_JOBS_DRY_RUN=True``  → submission simulated, status ``submitted``.
      - otherwise                       → real HTTP call via the internal client.
    """
    related_entity_id = str(related_entity_id) if related_entity_id else ""
    key = idempotency_key or default_idempotency_key(job_type, related_entity_id)

    # Idempotency: reuse a still-running job for the same entity + job type.
    existing = find_active_job(workspace=workspace, idempotency_key=key)
    if existing is not None:
        return existing, False

    # Resolve the provider from the registry unless explicitly given.
    if provider is None:
        provider = registry.resolve_provider(job_type)

    request_id = uuid.uuid4().hex

    # 1) Create the reference BEFORE any external call.
    job = ExternalJobReference.objects.create(
        workspace=workspace,
        job_type=job_type,
        provider=provider,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        requested_by=requested_by,
        request_id=request_id,
        idempotency_key=key,
        retry_count=retry_count,
        status=ExternalJobReference.Status.QUEUED,
        metadata=metadata or {},
    )

    # 2) Build and persist the request envelope.
    envelope = build_request_envelope(job, payload)
    job.request_payload = envelope
    job.save(update_fields=["request_payload", "updated_at"])
    log_job_event("job_created", job)

    # 3) Submit according to configuration.
    _submit_job(job, envelope)
    return job, True


def _submit_job(job, envelope) -> None:
    """Submit ``job`` to its external service, honouring enabled / dry-run."""
    if not registry.external_jobs_enabled():
        # Disabled: keep the job queued; nothing is called.
        _audit_submission(job, simulated=False, queued=True)
        log_job_event("job_queued", job, reason="external_jobs_disabled")
        return

    if registry.external_jobs_dry_run():
        # Dry-run: simulate a successful submission without any HTTP call.
        job.status = ExternalJobReference.Status.SUBMITTED
        job.submitted_at = now()
        job.response_payload = {"dry_run": True}
        job.save(update_fields=["status", "submitted_at", "response_payload", "updated_at"])
        _audit_submission(job, simulated=True, queued=False)
        log_job_event("job_submitted", job, dry_run=True)
        return

    # Real submission.
    try:
        endpoint = registry.resolve_service(job.job_type)
    except (registry.UnknownJobType, registry.ServiceNotConfigured) as exc:
        _mark_failed(job, str(exc))
        return

    client = InternalServiceClient(endpoint.base_url, endpoint.timeout)
    try:
        response = client.post_json(
            SUBMIT_PATH,
            envelope,
            workspace_id=job.workspace_id,
            job_id=job.id,
            request_id=job.request_id,
        )
    except InternalClientTimeout as exc:
        _mark_timeout(job, str(exc))
        return
    except InternalClientError as exc:
        body = getattr(exc, "body", "")
        _mark_failed(job, str(exc), response_payload={"error": body} if body else None)
        return

    job.status = ExternalJobReference.Status.SUBMITTED
    job.submitted_at = now()
    job.response_payload = response.data or {}
    # The service may return its own job id.
    external_id = (response.data or {}).get("external_job_id")
    update_fields = ["status", "submitted_at", "response_payload", "updated_at"]
    if external_id:
        job.external_job_id = str(external_id)
        update_fields.append("external_job_id")
    job.save(update_fields=update_fields)
    _audit_submission(job, simulated=False, queued=False)
    log_job_event("job_submitted", job)


def _mark_failed(job, message, *, response_payload=None) -> None:
    job.status = ExternalJobReference.Status.FAILED
    job.failed_at = now()
    job.error_message = message
    fields = ["status", "failed_at", "error_message", "updated_at"]
    if response_payload is not None:
        job.response_payload = response_payload
        fields.append("response_payload")
    job.save(update_fields=fields)
    _audit_submission(job, simulated=False, queued=False, failed=True)
    log_job_event("job_submission_failed", job, level=logging.WARNING)


def _mark_timeout(job, message) -> None:
    job.status = ExternalJobReference.Status.TIMEOUT
    job.failed_at = now()
    job.error_message = message
    job.save(update_fields=["status", "failed_at", "error_message", "updated_at"])
    _audit_submission(job, simulated=False, queued=False, failed=True)
    log_job_event("job_timeout", job, level=logging.WARNING)


def _audit_submission(job, *, simulated, queued, failed=False) -> None:
    """Record a best-effort audit event for the submission outcome."""
    try:
        from apps.audit.services import record_audit_event
    except ImportError:
        return
    if failed:
        action = "external_job.submission_failed"
    elif queued:
        action = "external_job.queued"
    else:
        action = "external_job.submitted"
    record_audit_event(
        action=action,
        workspace=job.workspace,
        actor_user=job.requested_by,
        actor_type=None if job.requested_by else "system",
        entity_type=job.related_entity_type or "external_job",
        entity_id=job.related_entity_id or job.id,
        after_data={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "provider": job.provider,
            "status": job.status,
            "request_id": job.request_id,
            "dry_run": simulated,
        },
    )


# --------------------------------------------------------------------------- #
# Retry
# --------------------------------------------------------------------------- #
class RetryNotAllowed(Exception):
    """Raised when a job is not in a retryable state."""


def retry_external_job(job, *, requested_by=None, payload=None):
    """Explicitly retry a job from a retryable terminal state.

    Creates a *new* job (the old one is preserved) with ``retry_count``
    incremented and a ``retried_from`` link. Raises :class:`RetryNotAllowed`
    unless the job is ``failed`` / ``timeout`` / ``cancelled`` / ``expired``.
    The new job reuses the same ``idempotency_key`` so a still-running retry is
    not duplicated.
    """
    if job.status not in ExternalJobReference.RETRYABLE_STATUSES:
        raise RetryNotAllowed(
            f"Job in status '{job.status}' cannot be retried "
            f"(allowed: {', '.join(ExternalJobReference.RETRYABLE_STATUSES)})."
        )
    # Reuse the original request payload's domain part when none is supplied.
    if payload is None:
        payload = (job.request_payload or {}).get("payload", {})
    metadata = dict(job.metadata or {})
    metadata["retried_from"] = str(job.id)
    new_job, _ = create_and_submit_external_job(
        workspace=job.workspace,
        job_type=job.job_type,
        provider=job.provider,
        related_entity_type=job.related_entity_type,
        related_entity_id=job.related_entity_id,
        requested_by=requested_by or job.requested_by,
        payload=payload,
        idempotency_key=job.idempotency_key,
        metadata=metadata,
        retry_count=job.retry_count + 1,
    )
    log_job_event("job_retried", new_job, retried_from=str(job.id))
    return new_job


# --------------------------------------------------------------------------- #
# Callback transition (kept; extended in the callback dispatcher phase)
# --------------------------------------------------------------------------- #
def apply_job_callback(job, *, status, error_message="", metadata=None):
    """Apply a callback state transition to ``job`` and return it.

    Sets the matching lifecycle timestamp for the new status and merges any
    supplied metadata. Callers are responsible for authenticating the caller.
    """
    job.status = status
    Status = ExternalJobReference.Status
    if status == Status.RUNNING and job.started_at is None:
        job.started_at = now()
    elif status in (Status.COMPLETED, Status.PARTIALLY_COMPLETED):
        job.completed_at = now()
    elif status in (Status.FAILED, Status.TIMEOUT, Status.EXPIRED):
        job.failed_at = now()
        job.error_message = error_message or job.error_message

    if metadata:
        merged = dict(job.metadata or {})
        merged.update(metadata)
        job.metadata = merged

    job.save(
        update_fields=[
            "status",
            "started_at",
            "completed_at",
            "failed_at",
            "error_message",
            "metadata",
            "updated_at",
        ]
    )
    return job
