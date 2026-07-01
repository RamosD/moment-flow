"""Cross-workspace isolation: a user of workspace A never reads or mutates B's data.

Data graphs are built directly with factories; isolation is asserted through the
real API (workspace resolved from the X-Workspace-ID header).
"""

import pytest

from tests import factories
from tests.conftest import ws_header

ARTISTS_URL = "/api/v1/artists/"
TRACKS_URL = "/api/v1/tracks/"
CAMPAIGNS_URL = "/api/v1/campaigns/"
SMART_LINKS_URL = "/api/v1/smart-links/"
CREDITS_URL = "/api/v1/billing/credits/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.fixture
def tenants(db, seeded, add_member):
    """Two fully isolated tenants, each with an owner member."""
    ws_a = factories.WorkspaceFactory()
    ws_b = factories.WorkspaceFactory()
    user_a = factories.UserFactory()
    user_b = factories.UserFactory()
    add_member(ws_a, user_a, "owner")
    add_member(ws_b, user_b, "owner")
    return ws_a, ws_b, user_a, user_b


@pytest.mark.django_db
class TestArtistIsolation:
    def test_b_cannot_list_a_artists(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        factories.ArtistFactory(workspace=ws_a)
        resp = auth_client(user_b).get(ARTISTS_URL, **ws_header(ws_b))
        assert resp.status_code == 200
        assert _results(resp) == []

    def test_b_cannot_read_a_artist_by_id(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        artist = factories.ArtistFactory(workspace=ws_a)
        resp = auth_client(user_b).get(f"{ARTISTS_URL}{artist.id}/", **ws_header(ws_b))
        assert resp.status_code == 404

    def test_b_cannot_modify_a_artist(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        artist = factories.ArtistFactory(workspace=ws_a, name="Original")
        resp = auth_client(user_b).patch(
            f"{ARTISTS_URL}{artist.id}/",
            {"name": "Hacked"},
            format="json",
            **ws_header(ws_b),
        )
        assert resp.status_code == 404
        artist.refresh_from_db()
        assert artist.name == "Original"

    def test_non_member_cannot_use_foreign_workspace_header(self, tenants, auth_client):
        ws_a, _ws_b, _user_a, user_b = tenants
        # user_b is not a member of ws_a → blocked at the membership check.
        resp = auth_client(user_b).get(ARTISTS_URL, **ws_header(ws_a))
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTrackIsolation:
    def test_b_cannot_read_a_track(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        track = factories.TrackFactory(workspace=ws_a)
        resp = auth_client(user_b).get(f"{TRACKS_URL}{track.id}/", **ws_header(ws_b))
        assert resp.status_code == 404


@pytest.mark.django_db
class TestCampaignIsolation:
    def test_b_cannot_list_a_campaigns(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        factories.CampaignFactory(workspace=ws_a)
        resp = auth_client(user_b).get(CAMPAIGNS_URL, **ws_header(ws_b))
        assert resp.status_code == 200
        assert _results(resp) == []

    def test_b_cannot_modify_a_campaign(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        campaign = factories.CampaignFactory(workspace=ws_a, name="Original")
        resp = auth_client(user_b).patch(
            f"{CAMPAIGNS_URL}{campaign.id}/",
            {"name": "Hacked"},
            format="json",
            **ws_header(ws_b),
        )
        assert resp.status_code == 404
        campaign.refresh_from_db()
        assert campaign.name == "Original"


@pytest.mark.django_db
class TestSmartLinkIsolation:
    def test_b_cannot_read_a_smart_link(self, tenants, auth_client):
        ws_a, ws_b, _user_a, user_b = tenants
        link = factories.SmartLinkFactory(workspace=ws_a)
        resp = auth_client(user_b).get(
            f"{SMART_LINKS_URL}{link.id}/", **ws_header(ws_b)
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestBillingIsolation:
    def test_credit_balance_is_per_workspace(self, tenants, auth_client):
        from apps.billing.services import grant_credits

        ws_a, ws_b, _user_a, user_b = tenants
        grant_credits(ws_a, 100)
        # B sees its own (zero) balance, never A's.
        resp = auth_client(user_b).get(CREDITS_URL, **ws_header(ws_b))
        assert resp.status_code == 200
        assert float(resp.data["balance"]) == 0.0
