"""Contracts for the FastAPI Intelligence Engine (metrics / moments / insights /
recommendations).

Django only *orchestrates*: it builds the request payload and opens an
``ExternalJobReference`` via ``create_and_submit_external_job``. It never collects
metrics, detects moments, or generates insights/recommendations — that is the
Intelligence Engine's job. The matching callbacks are handled by the placeholder
handlers in :mod:`apps.integrations_bridge.callbacks`, which only persist the
callback and audit it (no analytical model is created here).

Each builder returns the **domain** payload; the integrations-bridge envelope adds
the transport fields (``job_id``, ``request_id``, ``workspace_id``,
``callback_url``, ``entity``, ``payload_version``).
"""

from .models import ExternalJobReference
from .services import create_and_submit_external_job

PAYLOAD_VERSION = "1.0"


def _entity_for(campaign, track):
    """Primary product entity a technical job is attached to (track preferred)."""
    if track is not None:
        return "track", str(track.id)
    if campaign is not None:
        return "campaign", str(campaign.id)
    return "", ""


def _platform_links(workspace, track):
    """Track platform links (e.g. YouTube) the engine will collect metrics from."""
    if track is None:
        return []
    try:
        from apps.catalogue.models import TrackPlatformLink
    except ImportError:
        return []
    links = TrackPlatformLink.objects.filter(
        workspace=workspace, track=track
    ).order_by("created_at")
    return [
        {
            "id": str(link.id),
            "platform": link.platform,
            "external_id": link.external_id,
            "url": link.url,
            "canonical_url": link.canonical_url,
            "status": link.status,
        }
        for link in links
    ]


# --------------------------------------------------------------------------- #
# Payload builders
# --------------------------------------------------------------------------- #
def build_metrics_collection_payload(
    *, workspace, campaign=None, track=None, requested_by=None, metadata=None
):
    return {
        "payload_version": PAYLOAD_VERSION,
        "workspace_id": str(workspace.id),
        "campaign_id": str(campaign.id) if campaign else None,
        "track_id": str(track.id) if track else None,
        "platform_links": _platform_links(workspace, track),
        "requested_by": str(requested_by.id) if requested_by else None,
        "metadata": dict(metadata or {}),
    }


def build_moment_detection_payload(
    *, workspace, campaign=None, track=None, metrics_context=None
):
    return {
        "payload_version": PAYLOAD_VERSION,
        "workspace_id": str(workspace.id),
        "campaign_id": str(campaign.id) if campaign else None,
        "track_id": str(track.id) if track else None,
        "metrics_context": metrics_context or {},
    }


def build_insight_generation_payload(
    *, workspace, campaign=None, track=None, moments_context=None
):
    return {
        "payload_version": PAYLOAD_VERSION,
        "workspace_id": str(workspace.id),
        "campaign_id": str(campaign.id) if campaign else None,
        "track_id": str(track.id) if track else None,
        "moments_context": moments_context or {},
    }


def build_recommendation_generation_payload(
    *, workspace, campaign=None, track=None, insights_context=None
):
    return {
        "payload_version": PAYLOAD_VERSION,
        "workspace_id": str(workspace.id),
        "campaign_id": str(campaign.id) if campaign else None,
        "track_id": str(track.id) if track else None,
        "insights_context": insights_context or {},
    }


# --------------------------------------------------------------------------- #
# Request services (open & submit the technical job)
# --------------------------------------------------------------------------- #
def _request_job(
    *, workspace, job_type, payload, campaign, track, requested_by, idempotency_key=None
):
    """Open and submit a technical job. Honours dry-run / disabled via settings.

    ``idempotency_key`` defaults (in ``create_and_submit_external_job``) to
    ``"<job_type>:<entity_id>"``, so a still-running collection is reused rather
    than duplicated.
    """
    entity_type, entity_id = _entity_for(campaign, track)
    job, _created = create_and_submit_external_job(
        workspace=workspace,
        job_type=job_type,
        related_entity_type=entity_type,
        related_entity_id=entity_id,
        requested_by=requested_by,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return job


def request_metrics_collection(
    *, workspace, campaign=None, track=None, requested_by=None, metadata=None,
    idempotency_key=None,
):
    payload = build_metrics_collection_payload(
        workspace=workspace, campaign=campaign, track=track,
        requested_by=requested_by, metadata=metadata,
    )
    return _request_job(
        workspace=workspace,
        job_type=ExternalJobReference.JobType.METRICS_COLLECTION,
        payload=payload, campaign=campaign, track=track,
        requested_by=requested_by, idempotency_key=idempotency_key,
    )


def request_moment_detection(
    *, workspace, campaign=None, track=None, metrics_context=None, requested_by=None,
    idempotency_key=None,
):
    payload = build_moment_detection_payload(
        workspace=workspace, campaign=campaign, track=track,
        metrics_context=metrics_context,
    )
    return _request_job(
        workspace=workspace,
        job_type=ExternalJobReference.JobType.MOMENT_DETECTION,
        payload=payload, campaign=campaign, track=track,
        requested_by=requested_by, idempotency_key=idempotency_key,
    )


def request_insight_generation(
    *, workspace, campaign=None, track=None, moments_context=None, requested_by=None,
    idempotency_key=None,
):
    payload = build_insight_generation_payload(
        workspace=workspace, campaign=campaign, track=track,
        moments_context=moments_context,
    )
    return _request_job(
        workspace=workspace,
        job_type=ExternalJobReference.JobType.INSIGHT_GENERATION,
        payload=payload, campaign=campaign, track=track,
        requested_by=requested_by, idempotency_key=idempotency_key,
    )


def request_recommendation_generation(
    *, workspace, campaign=None, track=None, insights_context=None, requested_by=None,
    idempotency_key=None,
):
    payload = build_recommendation_generation_payload(
        workspace=workspace, campaign=campaign, track=track,
        insights_context=insights_context,
    )
    return _request_job(
        workspace=workspace,
        job_type=ExternalJobReference.JobType.RECOMMENDATION_GENERATION,
        payload=payload, campaign=campaign, track=track,
        requested_by=requested_by, idempotency_key=idempotency_key,
    )
