"""Intelligence Engine contracts: payload builders, request services, callbacks.

Django builds payloads and opens jobs, and stores callbacks — it never computes
metrics/moments/insights/recommendations.
"""

import json

import pytest

from apps.audit.models import AuditEvent
from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist, Track, TrackPlatformLink
from apps.integrations_bridge.intelligence import (
    build_metrics_collection_payload,
    request_insight_generation,
    request_metrics_collection,
    request_moment_detection,
    request_recommendation_generation,
)
from apps.integrations_bridge.models import ExternalJobReference

CALLBACK_URL = "/api/v1/internal/jobs/callback/"
TOKEN = "internal-secret-token"
_JT = ExternalJobReference.JobType


@pytest.fixture(autouse=True)
def _token(settings):
    settings.INTERNAL_API_TOKEN = TOKEN


def _auth(token=TOKEN):
    return {"HTTP_X_INTERNAL_TOKEN": token}


def _catalogue(workspace):
    artist = Artist.objects.create(workspace=workspace, name="Artist", slug="artist")
    track = Track.objects.create(
        workspace=workspace, artist=artist, title="Track", slug="track"
    )
    campaign = Campaign.objects.create(
        workspace=workspace, artist=artist, name="Campaign", slug="campaign"
    )
    link = TrackPlatformLink.objects.create(
        workspace=workspace, track=track,
        platform=TrackPlatformLink.Platform.YOUTUBE,
        external_id="vid123", url="https://www.youtube.com/watch?v=vid123",
    )
    return artist, track, campaign, link


# --------------------------------------------------------------------------- #
# Request services
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestRequestJobs:
    @pytest.mark.parametrize(
        "fn,job_type",
        [
            (request_metrics_collection, _JT.METRICS_COLLECTION),
            (request_moment_detection, _JT.MOMENT_DETECTION),
            (request_insight_generation, _JT.INSIGHT_GENERATION),
            (request_recommendation_generation, _JT.RECOMMENDATION_GENERATION),
        ],
    )
    def test_request_creates_job(self, fn, job_type, workspace, owner):
        _, track, campaign, _ = _catalogue(workspace)
        job = fn(workspace=workspace, campaign=campaign, track=track, requested_by=owner)
        assert job.job_type == job_type
        assert job.provider == "intelligence_engine"  # resolved via the registry
        assert job.related_entity_type == "track"
        assert job.related_entity_id == str(track.id)
        assert job.workspace_id == workspace.id

    def test_metrics_payload_includes_platform_links(self, workspace, owner):
        _, track, campaign, link = _catalogue(workspace)
        payload = build_metrics_collection_payload(
            workspace=workspace, campaign=campaign, track=track, requested_by=owner
        )
        json.dumps(payload)  # JSON serializable
        assert payload["track_id"] == str(track.id)
        assert payload["campaign_id"] == str(campaign.id)
        assert payload["requested_by"] == str(owner.id)
        assert len(payload["platform_links"]) == 1
        pl = payload["platform_links"][0]
        assert pl["platform"] == "youtube"
        assert pl["external_id"] == "vid123"
        assert pl["url"].endswith("v=vid123")

    def test_dry_run_marks_submitted(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = True
        settings.EXTERNAL_JOBS_DRY_RUN = True
        _, track, campaign, _ = _catalogue(workspace)
        job = request_metrics_collection(
            workspace=workspace, campaign=campaign, track=track, requested_by=owner
        )
        assert job.status == ExternalJobReference.Status.SUBMITTED
        assert job.response_payload == {"dry_run": True}

    def test_disabled_keeps_queued(self, settings, workspace, owner):
        settings.EXTERNAL_JOBS_ENABLED = False
        _, track, campaign, _ = _catalogue(workspace)
        job = request_metrics_collection(
            workspace=workspace, campaign=campaign, track=track, requested_by=owner
        )
        assert job.status == ExternalJobReference.Status.QUEUED

    def test_idempotent_per_track(self, workspace, owner):
        _, track, campaign, _ = _catalogue(workspace)
        a = request_metrics_collection(workspace=workspace, track=track, requested_by=owner)
        b = request_metrics_collection(workspace=workspace, track=track, requested_by=owner)
        assert a.id == b.id  # reused while non-terminal


# --------------------------------------------------------------------------- #
# Callbacks (placeholders — store only, no computation)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestCallbacks:
    @pytest.mark.parametrize(
        "fn,job_type,action",
        [
            (request_metrics_collection, _JT.METRICS_COLLECTION,
             "metrics_collection.callback_received"),
            (request_moment_detection, _JT.MOMENT_DETECTION,
             "moment_detection.callback_received"),
            (request_insight_generation, _JT.INSIGHT_GENERATION,
             "insight_generation.callback_received"),
            (request_recommendation_generation, _JT.RECOMMENDATION_GENERATION,
             "recommendation_generation.callback_received"),
        ],
    )
    def test_callback_stores_and_audits(
        self, api_client, workspace, owner, fn, job_type, action
    ):
        _, track, campaign, _ = _catalogue(workspace)
        job = fn(workspace=workspace, campaign=campaign, track=track, requested_by=owner)
        # A result the *engine* computed — Django must only store it, not derive.
        result = {"computed_by": "fastapi", "snapshots": [1, 2, 3], "views": 1000}
        resp = api_client.post(
            CALLBACK_URL,
            {
                "job_id": str(job.id),
                "workspace_id": str(workspace.id),
                "status": "completed",
                "entity": {"type": "track", "id": str(track.id)},
                "result": result,
            },
            format="json", **_auth(),
        )
        assert resp.status_code == 200
        job.refresh_from_db()
        assert job.status == ExternalJobReference.Status.COMPLETED
        assert job.callback_received_at is not None
        # Stored verbatim — proof Django does not compute anything itself.
        assert job.callback_payload.get("result") == result
        assert AuditEvent.objects.filter(action=action).count() == 1

    def test_django_does_not_compute_metrics(self, api_client, workspace, owner):
        # No metrics/moments/insights models exist; the callback only persists the
        # payload on the job. This guards the architectural boundary.
        _, track, campaign, _ = _catalogue(workspace)
        job = request_metrics_collection(
            workspace=workspace, campaign=campaign, track=track, requested_by=owner
        )
        api_client.post(
            CALLBACK_URL,
            {"job_id": str(job.id), "workspace_id": str(workspace.id),
             "status": "completed", "result": {"views": 5000}},
            format="json", **_auth(),
        )
        job.refresh_from_db()
        assert job.callback_payload.get("result") == {"views": 5000}
        # The audit trail records receipt only — never a computation action.
        assert not AuditEvent.objects.filter(
            action__in=["metrics.computed", "moment.detected", "insight.generated"]
        ).exists()
