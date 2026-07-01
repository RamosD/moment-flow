"""Quota enforcement: service-level and through real product flows."""

import pytest

from apps.billing.exceptions import QuotaExceeded
from apps.billing.services import check_workspace_limit, grant_credits
from apps.billing.tests.conftest import ws_header
from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.content.models import ContentPack, ContentPackRequest

ARTISTS_URL = "/api/v1/artists/"
REQUESTS_URL = "/api/v1/content-pack-requests/"


@pytest.mark.django_db
class TestCheckWorkspaceLimit:
    def test_fails_open_without_subscription(self, workspace):
        # No active plan → no enforceable limit → never blocks.
        check_workspace_limit(workspace, "artists_limit", current_count=999)

    def test_blocks_when_over_limit(self, workspace, subscribe):
        subscribe(workspace, "trial")  # artists_limit = 1
        check_workspace_limit(workspace, "artists_limit", current_count=0)
        with pytest.raises(QuotaExceeded):
            check_workspace_limit(workspace, "artists_limit", current_count=1)

    def test_unlimited_plan_never_blocks(self, workspace, subscribe):
        subscribe(workspace, "enterprise")  # artists_limit = None (unlimited)
        check_workspace_limit(workspace, "artists_limit", current_count=10_000)


@pytest.mark.django_db
class TestArtistQuotaThroughAPI:
    def test_artist_limit_blocks_creation(
        self, client_for, owner, workspace, subscribe
    ):
        subscribe(workspace, "trial")  # artists_limit = 1
        client = client_for(owner)

        first = client.post(
            ARTISTS_URL, {"name": "First"}, format="json", **ws_header(workspace)
        )
        assert first.status_code == 201

        second = client.post(
            ARTISTS_URL, {"name": "Second"}, format="json", **ws_header(workspace)
        )
        assert second.status_code == 402
        assert "artists_limit" in str(second.data)
        assert Artist.objects.filter(workspace=workspace).count() == 1

    def test_no_plan_does_not_block(self, client_for, owner, workspace):
        client = client_for(owner)
        for name in ("A", "B", "C"):
            resp = client.post(
                ARTISTS_URL, {"name": name}, format="json", **ws_header(workspace)
            )
            assert resp.status_code == 201


@pytest.mark.django_db
class TestContentPackCreditValidation:
    def _campaign(self, workspace):
        artist = Artist.objects.create(workspace=workspace, name="A", slug="a")
        return Campaign.objects.create(
            workspace=workspace, artist=artist, name="C", slug="c"
        )

    def _paid_pack(self, cost=5):
        return ContentPack.objects.create(
            pack_key="paid_pack",
            name="Paid Pack",
            pack_type=ContentPack.PackType.RELEASE_PACK,
            status=ContentPack.Status.ACTIVE,
            workspace=None,
            metadata={"credit_cost": cost},
        )

    def test_blocks_without_credits(self, client_for, owner, workspace):
        campaign = self._campaign(workspace)
        pack = self._paid_pack(cost=5)
        resp = client_for(owner).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 402
        # The failed attempt left no queued request behind.
        assert ContentPackRequest.objects.filter(workspace=workspace).count() == 0

    def test_succeeds_and_reserves_credits(self, client_for, owner, workspace):
        from apps.billing.services import get_credit_balance

        campaign = self._campaign(workspace)
        pack = self._paid_pack(cost=5)
        grant_credits(workspace, 10)

        resp = client_for(owner).post(
            REQUESTS_URL,
            {"campaign": str(campaign.id), "content_pack": str(pack.id)},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        # 10 granted, 5 reserved → 5 available.
        assert get_credit_balance(workspace) == 5
        request = ContentPackRequest.objects.get(id=resp.data["id"])
        assert request.usage_event_id is not None
