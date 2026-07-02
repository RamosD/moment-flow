"""Log correlation tests (OBS-STG-006).

Confirm the inter-service job flow carries the correlation identifiers
(`job_id`, `external_job_id`, `request_id`, `workspace_id`, `provider`, `status`),
that token-like extras never reach the logs, and that the project loggers are
configured to actually emit at INFO. The IE-flow `request_id` logging is already
covered by `test_intelligence_sync.py::test_logs_request_and_workspace_ids`.
"""

import logging

import pytest

from apps.integrations_bridge.logging_utils import job_log_fields, log_job_event


class _FakeJob:
    """A minimal stand-in for ExternalJobReference (no DB needed)."""

    def __init__(self, *, external_job_id=""):
        self.id = "job-uuid-1"
        self.workspace_id = "ws-1"
        self.external_job_id = external_job_id
        self.job_type = "content_generation"
        self.provider = "content_renderer"
        self.status = "submitted"
        self.request_id = "req-1"


class TestJobLogFields:
    def test_includes_external_job_id_when_present(self):
        fields = job_log_fields(_FakeJob(external_job_id="ext-77"))
        assert fields["external_job_id"] == "ext-77"
        assert fields["job_id"] == "job-uuid-1"
        assert fields["request_id"] == "req-1"
        assert fields["workspace_id"] == "ws-1"
        assert fields["provider"] == "content_renderer"
        assert fields["status"] == "submitted"

    def test_external_job_id_is_none_when_absent(self):
        fields = job_log_fields(_FakeJob(external_job_id=""))
        assert fields["external_job_id"] is None


class TestLogJobEvent:
    def test_event_carries_correlation_ids(self, caplog):
        with caplog.at_level(logging.INFO, logger="integrations_bridge"):
            log_job_event("job_submitted", _FakeJob(external_job_id="ext-77"))
        text = caplog.text
        assert "event=job_submitted" in text
        assert "job_id=job-uuid-1" in text
        assert "external_job_id=ext-77" in text
        assert "request_id=req-1" in text
        assert "workspace_id=ws-1" in text
        assert "provider=content_renderer" in text
        assert "status=submitted" in text

    def test_useful_on_failure_with_error_extras(self, caplog):
        with caplog.at_level(logging.WARNING, logger="integrations_bridge"):
            log_job_event(
                "job_submission_failed",
                _FakeJob(external_job_id="ext-9"),
                level=logging.WARNING,
                error_type="InternalServiceUnavailable",
            )
        text = caplog.text
        assert "event=job_submission_failed" in text
        assert "external_job_id=ext-9" in text
        assert "error_type=InternalServiceUnavailable" in text

    def test_token_like_extra_is_dropped(self, caplog):
        with caplog.at_level(logging.INFO, logger="integrations_bridge"):
            log_job_event(
                "job_submitted",
                _FakeJob(),
                token="super-secret-value",
                secret="another-secret",
                reason="ok",
            )
        text = caplog.text
        assert "super-secret-value" not in text
        assert "another-secret" not in text
        # Non-sensitive extras still appear.
        assert "reason=ok" in text


class TestLoggingConfig:
    @pytest.mark.parametrize(
        "name",
        [
            "integrations_bridge",
            "integrations_bridge.client",
            "integrations_bridge.intelligence",
            "campaigns.intelligence",
            # STG-PRE-005: creation events for CampaignAction/Report/MediaKit/
            # ContentPackRequest. Without an explicit LOGGING entry these would
            # silently never reach any handler at INFO (Python's last-resort
            # handler only surfaces WARNING+) — this test guards against that
            # regression (found and fixed during this same iteration).
            "campaign_actions.views",
            "reports.views",
            "content.services",
        ],
    )
    def test_loggers_emit_info(self, name):
        # The LOGGING config (settings.py) must let these loggers surface INFO.
        assert logging.getLogger(name).getEffectiveLevel() <= logging.INFO
