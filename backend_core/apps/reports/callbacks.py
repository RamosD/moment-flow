"""Report / media-kit generation callback effects (Django product side).

When the Report Renderer reports a ``report_generation`` or ``media_kit_generation``
job back, this module turns that result into product state: it creates the
``Asset`` (metadata only — no real file), links ``Report.storage_asset`` /
``MediaKit.storage_asset``, marks the entity completed/generated (or failed),
emits a notification and audits the outcome.

Expected ``result`` shape (completed) — the asset block may be at the top level
or under ``"asset"``::

    {
      "asset": {
        "title": "June Recap", "format": "pdf",
        "storage_provider": "s3", "bucket": "...", "storage_key": "...",
        "file_name": "report.pdf", "mime_type": "application/pdf",
        "file_size_bytes": 23456, "checksum": "...",
        "public_url": "https://.../report.pdf", "metadata": {}
      },
      "metadata": {}
    }

Idempotency: the dispatcher blocks re-dispatch once the job is terminal; on top of
that the asset is only created when the entity has no ``storage_asset`` yet, and
notifications are guarded by an ``event`` key — so a replay never duplicates an
Asset or a Notification, nor reopens a terminal entity.
"""

import logging
import uuid

from django.db import transaction

from apps.audit.services import record_audit_event
from apps.core.models import Asset
from apps.integrations_bridge.models import ExternalJobReference
from apps.integrations_bridge.services import apply_job_callback
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

from .models import MediaKit, Report

logger = logging.getLogger("reports.callbacks")

_FAILURE_STATUSES = {
    ExternalJobReference.Status.FAILED,
    ExternalJobReference.Status.TIMEOUT,
    ExternalJobReference.Status.EXPIRED,
}


def _controlled(job, entity, *, handled, note=""):
    return {
        "handled": handled,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "entity_id": str(entity.id) if entity else None,
        "note": note,
    }


def _resolve(model, job, expected_type):
    if job.related_entity_type != expected_type:
        return None
    try:
        uuid.UUID(str(job.related_entity_id))
    except (ValueError, TypeError, AttributeError):
        return None
    return model.objects.filter(id=job.related_entity_id).first()


def _asset_data(result):
    if not isinstance(result, dict):
        return {}
    sub = result.get("asset")
    if isinstance(sub, dict):
        return sub
    return result


def _error_message(error, error_message):
    if error_message:
        return error_message
    if isinstance(error, dict):
        return error.get("message", "")
    return ""


def _create_asset(workspace, asset_type, asset_data, *, created_by=None):
    meta = dict(asset_data.get("metadata") or {})
    if asset_data.get("format"):
        meta.setdefault("format", asset_data["format"])
    if asset_data.get("title"):
        meta.setdefault("title", asset_data["title"])
    return Asset.objects.create(
        workspace=workspace,
        asset_type=asset_type,
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
        public_url=asset_data.get("public_url", ""),
        created_by=created_by,
        metadata=meta,
    )


def _notify_once(
    workspace, *, entity_type, entity_id, user, event, notification_type, title, message=""
):
    for existing in Notification.objects.filter(
        workspace=workspace,
        related_entity_type=entity_type,
        related_entity_id=str(entity_id),
    ):
        if (existing.metadata or {}).get("event") == event:
            return existing
    return create_notification(
        workspace=workspace,
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_entity_type=entity_type,
        related_entity_id=str(entity_id),
        metadata={"event": event},
    )


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def apply_report_generation_callback(
    job, *, status, result=None, error=None, error_message="", metadata=None
):
    report = _resolve(Report, job, "report")
    if report is None:
        apply_job_callback(job, status=status, error_message=error_message, metadata=metadata)
        return _controlled(job, None, handled=False, note="report not found")
    if status in _FAILURE_STATUSES:
        return _report_failed(job, report, status, error, error_message, metadata)
    return _report_completed(job, report, status, result or {}, metadata)


@transaction.atomic
def _report_completed(job, report, status, result, metadata):
    asset_data = _asset_data(result)
    # The Asset model has no dedicated "report_html" type; both PDF and HTML
    # reports use REPORT_PDF and keep the concrete format/mime on the asset.
    if report.storage_asset_id is None and asset_data:
        report.storage_asset = _create_asset(
            report.workspace, Asset.AssetType.REPORT_PDF, asset_data,
            created_by=report.requested_by,
        )
    report.status = Report.Status.COMPLETED
    if isinstance(result.get("metadata"), dict):
        report.metadata = {**(report.metadata or {}), **result["metadata"]}
    report.save(update_fields=["status", "storage_asset", "metadata", "updated_at"])

    _notify_once(
        report.workspace,
        entity_type="report", entity_id=report.id, user=report.requested_by,
        event="report_ready",
        notification_type=Notification.NotificationType.REPORT_READY,
        title="Your report is ready", message=report.title,
    )
    record_audit_event(
        action="report.completed",
        workspace=report.workspace, actor_type="system",
        entity_type="report", entity_id=report.id,
        after_data={
            "status": report.status,
            "has_asset": report.storage_asset_id is not None,
        },
    )
    apply_job_callback(job, status=status, metadata=metadata)
    return _controlled(job, report, handled=True, note="report completed, asset linked")


@transaction.atomic
def _report_failed(job, report, status, error, error_message, metadata):
    message = _error_message(error, error_message)
    report.status = Report.Status.FAILED
    report.metadata = {**(report.metadata or {}), "error": message}
    report.save(update_fields=["status", "metadata", "updated_at"])

    _notify_once(
        report.workspace,
        entity_type="report", entity_id=report.id, user=report.requested_by,
        event="report_failed",
        notification_type=Notification.NotificationType.SYSTEM,
        title="Report generation failed", message=message or "The report could not be generated.",
    )
    record_audit_event(
        action="report.failed",
        workspace=report.workspace, actor_type="system",
        entity_type="report", entity_id=report.id,
        after_data={"status": report.status, "error": message},
    )
    apply_job_callback(job, status=status, error_message=message, metadata=metadata)
    return _controlled(job, report, handled=True, note="report failed")


# --------------------------------------------------------------------------- #
# Media kit
# --------------------------------------------------------------------------- #
def apply_media_kit_generation_callback(
    job, *, status, result=None, error=None, error_message="", metadata=None
):
    media_kit = _resolve(MediaKit, job, "media_kit")
    if media_kit is None:
        apply_job_callback(job, status=status, error_message=error_message, metadata=metadata)
        return _controlled(job, None, handled=False, note="media_kit not found")
    if status in _FAILURE_STATUSES:
        return _media_kit_failed(job, media_kit, status, error, error_message, metadata)
    return _media_kit_completed(job, media_kit, status, result or {}, metadata)


@transaction.atomic
def _media_kit_completed(job, media_kit, status, result, metadata):
    asset_data = _asset_data(result)
    if media_kit.storage_asset_id is None and asset_data:
        media_kit.storage_asset = _create_asset(
            media_kit.workspace, Asset.AssetType.MEDIA_KIT_ASSET, asset_data,
            created_by=media_kit.created_by,
        )
    media_kit.status = MediaKit.Status.GENERATED
    if isinstance(result.get("metadata"), dict):
        media_kit.metadata = {**(media_kit.metadata or {}), **result["metadata"]}
    media_kit.save(update_fields=["status", "storage_asset", "metadata", "updated_at"])

    _notify_once(
        media_kit.workspace,
        entity_type="media_kit", entity_id=media_kit.id, user=media_kit.created_by,
        event="media_kit_ready",
        notification_type=Notification.NotificationType.MEDIA_KIT_READY,
        title="Your media kit is ready", message=media_kit.title,
    )
    record_audit_event(
        action="media_kit.completed",
        workspace=media_kit.workspace, actor_type="system",
        entity_type="media_kit", entity_id=media_kit.id,
        after_data={
            "status": media_kit.status,
            "has_asset": media_kit.storage_asset_id is not None,
        },
    )
    apply_job_callback(job, status=status, metadata=metadata)
    return _controlled(job, media_kit, handled=True, note="media kit generated, asset linked")


@transaction.atomic
def _media_kit_failed(job, media_kit, status, error, error_message, metadata):
    message = _error_message(error, error_message)
    # MediaKit has no FAILED status — record the failure on metadata (documented).
    media_kit.metadata = {
        **(media_kit.metadata or {}),
        "generation_status": "failed",
        "error": message,
    }
    media_kit.save(update_fields=["metadata", "updated_at"])

    _notify_once(
        media_kit.workspace,
        entity_type="media_kit", entity_id=media_kit.id, user=media_kit.created_by,
        event="media_kit_failed",
        notification_type=Notification.NotificationType.SYSTEM,
        title="Media kit generation failed",
        message=message or "The media kit could not be generated.",
    )
    record_audit_event(
        action="media_kit.failed",
        workspace=media_kit.workspace, actor_type="system",
        entity_type="media_kit", entity_id=media_kit.id,
        after_data={"generation_status": "failed", "error": message},
    )
    apply_job_callback(job, status=status, error_message=message, metadata=metadata)
    return _controlled(job, media_kit, handled=True, note="media kit failed (recorded in metadata)")
