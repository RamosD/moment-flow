"""Billing regression: idempotent usage, credit lifecycle and quota enforcement."""

from decimal import Decimal

import pytest

from apps.billing.exceptions import InsufficientCredits
from apps.billing.models import Plan, Subscription, UsageEvent
from apps.billing.services import (
    consume_credits,
    get_credit_balance,
    grant_credits,
    record_usage_event,
    refund_credits,
    release_reserved_credits,
    reserve_credits,
)
from tests import factories
from tests.conftest import ws_header

ARTISTS_URL = "/api/v1/artists/"


@pytest.mark.django_db
class TestUsageIdempotency:
    def test_same_key_does_not_duplicate(self):
        workspace = factories.WorkspaceFactory()
        _e1, c1 = record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.ARTIST_CREATED,
            idempotency_key="k1",
        )
        _e2, c2 = record_usage_event(
            workspace=workspace,
            event_type=UsageEvent.EventType.ARTIST_CREATED,
            idempotency_key="k1",
        )
        assert c1 is True and c2 is False
        assert UsageEvent.objects.filter(workspace=workspace).count() == 1


@pytest.mark.django_db
class TestCreditLifecycle:
    def test_grant_increases_balance(self):
        workspace = factories.WorkspaceFactory()
        grant_credits(workspace, 100)
        assert get_credit_balance(workspace) == Decimal("100")

    def test_reserve_consume_release_refund(self):
        workspace = factories.WorkspaceFactory()
        grant_credits(workspace, 100)

        reserve_credits(workspace, 30)
        assert get_credit_balance(workspace) == Decimal("70")

        release_reserved_credits(workspace, 30)
        assert get_credit_balance(workspace) == Decimal("100")

        consume_credits(workspace, 40)
        assert get_credit_balance(workspace) == Decimal("60")

        refund_credits(workspace, 40)
        assert get_credit_balance(workspace) == Decimal("100")

    def test_settle_reserved_does_not_double_charge(self):
        workspace = factories.WorkspaceFactory()
        grant_credits(workspace, 50)
        reserve_credits(workspace, 50)
        assert get_credit_balance(workspace) == Decimal("0")
        consume_credits(workspace, 50, settle_reserved=True)
        assert get_credit_balance(workspace) == Decimal("0")

    def test_block_without_credits(self):
        workspace = factories.WorkspaceFactory()
        with pytest.raises(InsufficientCredits):
            reserve_credits(workspace, 10)
        with pytest.raises(InsufficientCredits):
            consume_credits(workspace, 10)

    def test_consume_is_idempotent(self):
        workspace = factories.WorkspaceFactory()
        grant_credits(workspace, 100)
        consume_credits(workspace, 30, idempotency_key="c1")
        consume_credits(workspace, 30, idempotency_key="c1")
        assert get_credit_balance(workspace) == Decimal("70")


@pytest.mark.django_db
class TestQuotaEnforcement:
    def test_campaign_limit_blocks_creation(self, seeded, add_member):
        # Trial plan: campaigns_limit = 1.
        workspace = factories.WorkspaceFactory()
        owner = factories.UserFactory()
        add_member(workspace, owner, "owner")
        Subscription.objects.create(
            workspace=workspace,
            plan=Plan.objects.get(plan_key="trial"),
            provider=Subscription.Provider.MANUAL,
            status=Subscription.Status.ACTIVE,
        )
        artist = factories.ArtistFactory(workspace=workspace)

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=owner)

        first = client.post(
            "/api/v1/campaigns/",
            {"name": "C1", "artist": str(artist.id)},
            format="json",
            **ws_header(workspace),
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/campaigns/",
            {"name": "C2", "artist": str(artist.id)},
            format="json",
            **ws_header(workspace),
        )
        assert second.status_code == 402
        assert "campaigns_limit" in str(second.data)

    def test_no_subscription_does_not_block(self, seeded, add_member):
        workspace = factories.WorkspaceFactory()
        owner = factories.UserFactory()
        add_member(workspace, owner, "owner")
        artist = factories.ArtistFactory(workspace=workspace)

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=owner)
        for i in range(3):
            resp = client.post(
                "/api/v1/campaigns/",
                {"name": f"C{i}", "artist": str(artist.id)},
                format="json",
                **ws_header(workspace),
            )
            assert resp.status_code == 201
