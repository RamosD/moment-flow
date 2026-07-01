"""Content-generation callback effects (Django product side).

When the Content Renderer reports a ``content_generation`` job back, this module
turns that result into product state: it updates the ``ContentPackRequest`` and
``ContentOutput`` entities, creates ``Asset`` rows for generated files, settles or
releases the reserved credits, records usage, emits a notification and audits the
outcome. **No rendering and no real files** are produced here — only metadata
supplied by the renderer is persisted.

Expected ``result`` shape (completed / partially_completed)::

    {
      "outputs": [
        {
          "output_type": "post",
          "format": "png",
          "status": "completed",            # or "failed"
          "title": "...", "caption": "...", "cta": "...",
          "required": true,                  # optional; drives credit decision
          "template_key": "system_post",     # or "template_id"
          "asset": {                          # optional; only for completed files
            "storage_provider": "s3", "bucket": "...", "storage_key": "...",
            "file_name": "...", "mime_type": "image/png",
            "file_size_bytes": 12345, "width": 1080, "height": 1080,
            "duration_seconds": null, "checksum": "..."
          },
          "metadata": {}
        }
      ]
    }

Idempotency: the callback dispatcher already blocks re-dispatch once the job is
terminal, and on top of that every side effect is keyed
(``content_pack_generated:<id>``, ``content_pack_consume:<id>``,
``content_pack_release:<id>``, per-output ``external_output_key``, and a
notification ``event`` guard) so a replay never duplicates an Asset, Notification,
UsageEvent or credit movement.
"""

import logging
import uuid

from django.db import transaction
from django.utils.timezone import now

from apps.audit.services import record_audit_event
from apps.billing.models import UsageEvent
from apps.billing.services import (
    consume_credits,
    record_usage_event,
    release_reserved_credits,
)
from apps.core.models import Asset
from apps.integrations_bridge.models import ExternalJobReference
from apps.integrations_bridge.services import apply_job_callback
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

from .models import ContentOutput, ContentPackRequest, Template, TemplateVersion
from .services import _pack_credit_cost

logger = logging.getLogger("content.callbacks")

_OUTPUT_STATUS = {
    "completed": ContentOutput.Status.COMPLETED,
    "failed": ContentOutput.Status.FAILED,
    "processing": ContentOutput.Status.PROCESSING,
    "rendering": ContentOutput.Status.RENDERING,
    "queued": ContentOutput.Status.QUEUED,
}

_FAILURE_STATUSES = {
    ExternalJobReference.Status.FAILED,
    ExternalJobReference.Status.TIMEOUT,
    ExternalJobReference.Status.EXPIRED,
}


def _controlled(job, request, *, handled, note="", **extra):
    payload = {
        "handled": handled,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "request_id": str(request.id) if request else None,
        "note": note,
    }
    payload.update(extra)
    return payload


def _resolve_request(job):
    if job.related_entity_type != "content_pack_request":
        return None
    try:
        uuid.UUID(str(job.related_entity_id))
    except (ValueError, TypeError, AttributeError):
        return None
    return ContentPackRequest.objects.filter(id=job.related_entity_id).first()


def apply_content_generation_callback(
    job, *, status, result=None, error=None, error_message="", metadata=None
):
    """Entry point used by the integrations-bridge dispatcher."""
    request = _resolve_request(job)
    if request is None:
        # No product entity to update — just transition the job.
        apply_job_callback(job, status=status, error_message=error_message, metadata=metadata)
        return _controlled(job, None, handled=False, note="content_pack_request not found")

    if status in _FAILURE_STATUSES:
        return _handle_failed(job, request, status, error, error_message, metadata)
    return _handle_success(job, request, status, result or {}, metadata)


# --------------------------------------------------------------------------- #
# Success (completed / partially_completed)
# --------------------------------------------------------------------------- #
@transaction.atomic
def _handle_success(job, request, status, result, metadata):
    outputs_data = result.get("outputs", []) or []
    existing_by_key = _existing_outputs_by_key(request)

    completed_count = 0
    failed_count = 0
    skipped = 0
    for index, output_data in enumerate(outputs_data):
        output = _upsert_output(request, output_data, index, existing_by_key)
        if output is None:
            skipped += 1
            continue
        if output.status == ContentOutput.Status.COMPLETED:
            completed_count += 1
        elif output.status == ContentOutput.Status.FAILED:
            failed_count += 1

    produced = completed_count > 0

    # Credits: consume reserved when something usable was generated, else release.
    credit_cost = _pack_credit_cost(request.content_pack)
    if credit_cost > 0:
        if _should_consume(status, outputs_data):
            consume_credits(
                request.workspace,
                credit_cost,
                settle_reserved=True,
                reason=f"content_pack:{request.content_pack.pack_key}",
                related_entity_type="content_pack_request",
                related_entity_id=str(request.id),
                idempotency_key=f"content_pack_consume:{request.id}",
            )
        else:
            release_reserved_credits(
                request.workspace,
                credit_cost,
                reason=f"content_pack_failed:{request.content_pack.pack_key}",
                related_entity_type="content_pack_request",
                related_entity_id=str(request.id),
                idempotency_key=f"content_pack_release:{request.id}",
            )

    # Usage event for the generation (idempotent), only when something produced.
    if produced:
        record_usage_event(
            workspace=request.workspace,
            event_type=UsageEvent.EventType.CONTENT_PACK_GENERATED,
            related_entity_type="content_pack_request",
            related_entity_id=str(request.id),
            idempotency_key=f"content_pack_generated:{request.id}",
        )

    # Request status.
    if status == ExternalJobReference.Status.PARTIALLY_COMPLETED:
        request.status = ContentPackRequest.Status.PARTIALLY_COMPLETED
    else:
        request.status = ContentPackRequest.Status.COMPLETED
    request.completed_at = now()
    request.save(update_fields=["status", "completed_at", "updated_at"])

    # Notification + audit.
    if produced:
        _notify_once(
            request,
            event="content_pack_ready",
            notification_type=Notification.NotificationType.CONTENT_READY,
            title="Your content pack is ready",
            message=f"{completed_count} output(s) generated for your content pack.",
        )
    else:
        _notify_once(
            request,
            event="content_pack_failed",
            notification_type=Notification.NotificationType.SYSTEM,
            title="Content pack generation failed",
            message="No outputs could be generated.",
        )
    record_audit_event(
        action="content_pack.completed",
        workspace=request.workspace,
        actor_type="system",
        entity_type="content_pack_request",
        entity_id=request.id,
        after_data={
            "request_status": request.status,
            "completed": completed_count,
            "failed": failed_count,
            "skipped": skipped,
        },
    )

    # Finally transition the job (completed / partially_completed).
    apply_job_callback(job, status=status, metadata=metadata)
    return _controlled(
        job, request, handled=True,
        note="outputs/assets/credits applied",
        completed=completed_count, failed=failed_count, skipped=skipped,
    )


# --------------------------------------------------------------------------- #
# Failure
# --------------------------------------------------------------------------- #
@transaction.atomic
def _handle_failed(job, request, status, error, error_message, metadata):
    message = error_message
    if not message and isinstance(error, dict):
        message = error.get("message", "")

    # Mark any existing outputs as failed.
    request.outputs.exclude(status=ContentOutput.Status.FAILED).update(
        status=ContentOutput.Status.FAILED
    )

    # Release the reserved credits (failure must not charge the customer).
    credit_cost = _pack_credit_cost(request.content_pack)
    if credit_cost > 0:
        release_reserved_credits(
            request.workspace,
            credit_cost,
            reason=f"content_pack_failed:{request.content_pack.pack_key}",
            related_entity_type="content_pack_request",
            related_entity_id=str(request.id),
            idempotency_key=f"content_pack_release:{request.id}",
        )

    request.status = ContentPackRequest.Status.FAILED
    request.failed_at = now()
    request.error_message = message or request.error_message
    request.save(update_fields=["status", "failed_at", "error_message", "updated_at"])

    _notify_once(
        request,
        event="content_pack_failed",
        notification_type=Notification.NotificationType.SYSTEM,
        title="Content pack generation failed",
        message=message or "The content pack could not be generated.",
    )
    record_audit_event(
        action="content_pack.failed",
        workspace=request.workspace,
        actor_type="system",
        entity_type="content_pack_request",
        entity_id=request.id,
        after_data={"request_status": request.status, "error": message},
    )

    apply_job_callback(job, status=status, error_message=message, metadata=metadata)
    return _controlled(job, request, handled=True, note="request failed, credits released")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _existing_outputs_by_key(request):
    mapping = {}
    for output in request.outputs.all():
        key = (output.metadata or {}).get("external_output_key")
        if key:
            mapping[key] = output
    return mapping


def _output_key(output_data, index):
    explicit = output_data.get("id")
    if explicit:
        return str(explicit)
    return f"{output_data.get('output_type', '')}|{output_data.get('template_key', '')}|{index}"


def _resolve_template(request, output_data):
    template_id = output_data.get("template_id")
    if template_id:
        template = Template.objects.filter(id=template_id).first()
        if template:
            return template
    template_key = output_data.get("template_key")
    if template_key:
        template = Template.objects.filter(template_key=template_key).first()
        if template:
            return template
    output_type = output_data.get("output_type")
    if output_type:
        link = (
            request.content_pack.pack_templates.filter(output_type=output_type)
            .select_related("template")
            .first()
        )
        if link:
            return link.template
    return None


def _create_asset(request, asset_data):
    return Asset.objects.create(
        workspace=request.workspace,
        asset_type=Asset.AssetType.GENERATED_OUTPUT,
        storage_provider=asset_data.get("storage_provider", Asset.StorageProvider.LOCAL),
        bucket=asset_data.get("bucket", ""),
        storage_key=asset_data.get("storage_key", ""),
        file_name=asset_data.get("file_name", ""),
        mime_type=asset_data.get("mime_type", ""),
        file_size_bytes=asset_data.get("file_size_bytes"),
        width=asset_data.get("width"),
        height=asset_data.get("height"),
        duration_seconds=asset_data.get("duration_seconds"),
        checksum=asset_data.get("checksum", ""),
        created_by=request.requested_by,
        metadata=asset_data.get("metadata") or {},
    )


def _upsert_output(request, output_data, index, existing_by_key):
    """Create or update a single ContentOutput idempotently. Returns it (or None)."""
    key = _output_key(output_data, index)
    output = existing_by_key.get(key)
    template = _resolve_template(request, output_data)
    if output is None and template is None:
        logger.warning(
            "content output skipped (no template) request_id=%s key=%s",
            request.id, key,
        )
        return None

    out_status = _OUTPUT_STATUS.get(
        output_data.get("status"), ContentOutput.Status.COMPLETED
    )

    campaign = request.campaign
    if output is None:
        version = (
            TemplateVersion.objects.filter(
                template=template, status=TemplateVersion.Status.ACTIVE
            )
            .order_by("-created_at")
            .first()
        )
        output = ContentOutput(
            workspace=request.workspace,
            campaign=campaign,
            track=request.track or campaign.track,
            artist=request.artist or campaign.artist,
            content_pack_request=request,
            template=template,
            template_version=version,
            created_by=request.requested_by,
        )

    output.output_type = output_data.get("output_type", output.output_type or "")
    output.format = output_data.get("format", output.format or "")
    output.status = out_status
    output.title = output_data.get("title", output.title or "")
    output.caption = output_data.get("caption", output.caption or "")
    output.cta = output_data.get("cta", output.cta or "")
    output.metadata = {
        **(output.metadata or {}),
        **(output_data.get("metadata") or {}),
        "external_output_key": key,
    }

    # Create the Asset only for a completed output that has no asset yet.
    asset_data = output_data.get("asset")
    if (
        asset_data
        and out_status == ContentOutput.Status.COMPLETED
        and output.storage_asset_id is None
    ):
        output.storage_asset = _create_asset(request, asset_data)

    output.save()
    existing_by_key[key] = output
    return output


def _should_consume(status, outputs_data) -> bool:
    """Credit rule for partial success (see module/report docs).

    - completed → consume.
    - partially_completed → consume if at least one *required* output succeeded
      (falling back to "any output succeeded" when no required flag is present),
      otherwise release.
    """
    if status == ExternalJobReference.Status.COMPLETED:
        return True
    required = [o for o in outputs_data if o.get("required")]
    pool = required or outputs_data
    return any(o.get("status") == "completed" for o in pool)


def _notify_once(request, *, event, notification_type, title, message=""):
    """Create a notification unless one for this (request, event) already exists."""
    for existing in Notification.objects.filter(
        workspace=request.workspace,
        related_entity_type="content_pack_request",
        related_entity_id=str(request.id),
    ):
        if (existing.metadata or {}).get("event") == event:
            return existing
    return create_notification(
        workspace=request.workspace,
        user=request.requested_by,
        notification_type=notification_type,
        title=title,
        message=message,
        related_entity_type="content_pack_request",
        related_entity_id=str(request.id),
        metadata={"event": event},
    )
