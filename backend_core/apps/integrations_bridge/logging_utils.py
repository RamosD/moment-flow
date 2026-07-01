"""Structured, token-free logging for the integrations bridge.

``log_job_event`` emits a single ``key=value`` line with the standard job-tracing
fields (workspace_id, job_id, job_type, provider, status, request_id). It never
logs the internal token nor full request/response/callback payloads — only ids
and small, non-sensitive extras passed explicitly by the caller.
"""

import logging

logger = logging.getLogger("integrations_bridge")

# Fields that must never be logged, even if passed as an extra.
_FORBIDDEN_KEYS = {"token", "internal_token", "x_internal_token", "secret", "password"}


def job_log_fields(job) -> dict:
    """Standard tracing fields for a job (no secrets, no payloads).

    ``external_job_id`` (the id assigned by the external service, when known) is
    included so renderer callbacks — which may be resolved by ``external_job_id``
    rather than the internal ``job_id`` — stay correlatable. It is ``None`` until
    the external service reports one.
    """
    return {
        "workspace_id": str(job.workspace_id) if job.workspace_id else None,
        "job_id": str(job.id),
        "external_job_id": job.external_job_id or None,
        "job_type": job.job_type,
        "provider": job.provider,
        "status": job.status,
        "request_id": job.request_id,
    }


def log_job_event(event, job, *, level=logging.INFO, log=logger, **extra):
    """Log a job lifecycle ``event`` with the standard tracing fields.

    ``extra`` is for small, non-sensitive values (e.g. ``reason``,
    ``retried_from``). Forbidden keys are dropped defensively.
    """
    fields = {"event": event, **job_log_fields(job)}
    for key, value in extra.items():
        if key.lower() in _FORBIDDEN_KEYS:
            continue
        fields[key] = value
    log.log(level, " ".join(f"{k}={v}" for k, v in fields.items()))
