"""Usage events: idempotency and the period-usage endpoint."""

import pytest

from apps.billing.models import UsageEvent
from apps.billing.services import current_billing_period, record_usage_event
from apps.billing.tests.conftest import ws_header

USAGE_URL = "/api/v1/billing/usage/"


@pytest.mark.django_db
class TestUsageIdempotency:
    def test_records_event(self, workspace):
        event, created = record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.ARTIST_CREATED,
            idempotency_key="art-1",
        )
        assert created is True
        assert event.billing_period == current_billing_period()

    def test_same_idempotency_key_does_not_duplicate(self, workspace):
        first, c1 = record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.TRACK_CREATED,
            idempotency_key="track-1",
        )
        second, c2 = record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.TRACK_CREATED,
            idempotency_key="track-1",
        )
        assert c1 is True
        assert c2 is False
        assert first.id == second.id
        assert UsageEvent.objects.filter(workspace=workspace).count() == 1

    def test_without_key_allows_multiple(self, workspace):
        record_usage_event(
            workspace=workspace, event_type=UsageEvent.EventType.SMART_LINK_CLICKED
        )
        record_usage_event(
            workspace=workspace, event_type=UsageEvent.EventType.SMART_LINK_CLICKED
        )
        assert UsageEvent.objects.filter(workspace=workspace).count() == 2

    def test_idempotency_scoped_per_workspace(self, workspace, other_workspace):
        record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.ARTIST_CREATED,
            idempotency_key="shared-key",
        )
        _, created = record_usage_event(
            workspace=other_workspace,
            event_type=UsageEvent.EventType.ARTIST_CREATED,
            idempotency_key="shared-key",
        )
        assert created is True  # same key, different workspace → not a duplicate


@pytest.mark.django_db
class TestPeriodUsageAPI:
    def test_returns_aggregated_usage(self, client_for, owner, workspace):
        for i in range(3):
            record_usage_event(
                workspace=workspace,
                event_type=UsageEvent.EventType.CONTENT_PACK_REQUESTED,
                cost_units=2,
                idempotency_key=f"cp-{i}",
            )
        resp = client_for(owner).get(USAGE_URL, **ws_header(workspace))
        assert resp.status_code == 200
        assert resp.data["billing_period"] == current_billing_period()
        row = next(
            r for r in resp.data["usage"]
            if r["event_type"] == UsageEvent.EventType.CONTENT_PACK_REQUESTED
        )
        assert row["events"] == 3
        assert float(row["total_cost"]) == 6.0
