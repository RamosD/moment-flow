"""Callback dispatcher: route an internal job callback to a per-type handler.

This phase deliberately keeps handlers thin. Content / report / media-kit
handlers only transition the *job* state and return a controlled structure —
updating product entities (ContentOutput, Asset, Report, MediaKit), consuming
credits and emitting notifications is done in later phases. Intelligence-engine
handlers (metrics / moments / insights / recommendations) are placeholders: they
persist the callback and record a simple audit event, with **no** analytical
computation in Django.

The inbound payload has already been validated and ``callback_payload`` /
``callback_received_at`` persisted by the view before dispatch.
"""

from .models import ExternalJobReference
from .services import apply_job_callback


def _audit(job, action_suffix):
    """Best-effort audit of a callback (never breaks the callback)."""
    try:
        from apps.audit.services import record_audit_event
    except ImportError:
        return
    record_audit_event(
        action=f"{job.job_type}.{action_suffix}",
        workspace=job.workspace,
        actor_type="system",
        entity_type=job.related_entity_type or "external_job",
        entity_id=job.related_entity_id or job.id,
        after_data={
            "job_id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
        },
    )


def _transition(job, *, status, error_message="", metadata=None):
    apply_job_callback(job, status=status, error_message=error_message, metadata=metadata)


def _controlled(job, *, handled, note=""):
    return {
        "handled": handled,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "note": note,
    }


# --------------------------------------------------------------------------- #
# Renderer handlers (job state only in this phase)
# --------------------------------------------------------------------------- #
def handle_content_generation_callback(job, *, status, result, error, error_message, metadata):
    # Delegate the product effects (outputs/assets/credits/usage/notification) to
    # the content app, keeping this bridge generic. Imported lazily to avoid an
    # import cycle (content imports integrations_bridge.services).
    from apps.content.callbacks import apply_content_generation_callback

    return apply_content_generation_callback(
        job,
        status=status,
        result=result,
        error=error,
        error_message=error_message,
        metadata=metadata,
    )


def handle_content_preview_callback(job, *, status, result, error, error_message, metadata):
    # Previews are transient: only the job state is updated (no outputs/credits).
    _transition(job, status=status, error_message=error_message, metadata=metadata)
    _audit(job, "callback_received")
    return _controlled(job, handled=True, note="preview — no product entities created")


def handle_report_generation_callback(job, *, status, result, error, error_message, metadata):
    # Delegate the product effects (asset/notification/status) to the reports app.
    from apps.reports.callbacks import apply_report_generation_callback

    return apply_report_generation_callback(
        job, status=status, result=result, error=error,
        error_message=error_message, metadata=metadata,
    )


def handle_media_kit_generation_callback(job, *, status, result, error, error_message, metadata):
    from apps.reports.callbacks import apply_media_kit_generation_callback

    return apply_media_kit_generation_callback(
        job, status=status, result=result, error=error,
        error_message=error_message, metadata=metadata,
    )


# --------------------------------------------------------------------------- #
# Intelligence-engine placeholders (no computation in Django)
# --------------------------------------------------------------------------- #
def handle_metrics_collection_callback(job, *, status, result, error, error_message, metadata):
    _transition(job, status=status, error_message=error_message, metadata=metadata)
    _audit(job, "callback_received")
    return _controlled(job, handled=True, note="placeholder — no analytical logic in Django")


def handle_moment_detection_callback(job, *, status, result, error, error_message, metadata):
    _transition(job, status=status, error_message=error_message, metadata=metadata)
    _audit(job, "callback_received")
    return _controlled(job, handled=True, note="placeholder — no analytical logic in Django")


def handle_insight_generation_callback(job, *, status, result, error, error_message, metadata):
    _transition(job, status=status, error_message=error_message, metadata=metadata)
    _audit(job, "callback_received")
    return _controlled(job, handled=True, note="placeholder — no analytical logic in Django")


def handle_recommendation_generation_callback(
    job, *, status, result, error, error_message, metadata
):
    _transition(job, status=status, error_message=error_message, metadata=metadata)
    _audit(job, "callback_received")
    return _controlled(job, handled=True, note="placeholder — no analytical logic in Django")


def handle_unknown_job_callback(job, *, status, result, error, error_message, metadata):
    """Fallback for job types without a dedicated handler — never crashes."""
    _transition(job, status=status, error_message=error_message, metadata=metadata)
    _audit(job, "callback_unhandled")
    return _controlled(job, handled=False, note="no dedicated handler for this job_type")


_JT = ExternalJobReference.JobType
_HANDLERS = {
    _JT.CONTENT_GENERATION: handle_content_generation_callback,
    _JT.CONTENT_PREVIEW: handle_content_preview_callback,
    _JT.REPORT_GENERATION: handle_report_generation_callback,
    _JT.MEDIA_KIT_GENERATION: handle_media_kit_generation_callback,
    _JT.METRICS_COLLECTION: handle_metrics_collection_callback,
    _JT.MOMENT_DETECTION: handle_moment_detection_callback,
    _JT.INSIGHT_GENERATION: handle_insight_generation_callback,
    _JT.RECOMMENDATION_GENERATION: handle_recommendation_generation_callback,
}


def callback_dispatcher(job, *, status, result=None, error=None, error_message="", metadata=None):
    """Route a validated callback to the handler for ``job.job_type``.

    Returns the handler's controlled structure. Unknown job types fall back to a
    safe no-op handler (the endpoint never breaks).
    """
    handler = _HANDLERS.get(job.job_type, handle_unknown_job_callback)
    return handler(
        job,
        status=status,
        result=result,
        error=error,
        error_message=error_message,
        metadata=metadata,
    )
