"""CRUD, isolation, constraints and filter tests for campaigns."""

import pytest

from apps.campaigns.models import Campaign, CampaignGoal, CampaignTrack
from apps.campaigns.tests.conftest import ws_header

CAMPAIGNS_URL = "/api/v1/campaigns/"
TRACKS_URL = "/api/v1/campaign-tracks/"
GOALS_URL = "/api/v1/campaign-goals/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestCampaignCrud:
    def test_owner_creates_campaign_for_artist(
        self, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace, "Daft Punk", "daft-punk")
        resp = client_for(owner).post(
            CAMPAIGNS_URL,
            {
                "artist": str(artist.id),
                "name": "Discovery Relaunch",
                "campaign_type": "album_release",
                "status": "active",
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        assert resp.data["slug"] == "discovery-relaunch"
        campaign = Campaign.objects.get(id=resp.data["id"])
        assert campaign.workspace_id == workspace.id
        assert campaign.created_by_id == owner.id
        assert campaign.campaign_type == "album_release"
        assert campaign.status == "active"

    def test_campaign_with_track_same_workspace(
        self, client_for, owner, workspace, make_artist, make_track
    ):
        artist = make_artist(workspace)
        track = make_track(workspace, artist)
        resp = client_for(owner).post(
            CAMPAIGNS_URL,
            {"artist": str(artist.id), "track": str(track.id), "name": "Single Push"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        assert str(Campaign.objects.get(id=resp.data["id"]).track_id) == str(track.id)


@pytest.mark.django_db
class TestCampaignWorkspaceIsolation:
    def test_rejects_artist_from_other_workspace(
        self, client_for, owner, workspace, other_workspace, make_artist
    ):
        foreign_artist = make_artist(other_workspace, "Foreign", "foreign")
        resp = client_for(owner).post(
            CAMPAIGNS_URL,
            {"artist": str(foreign_artist.id), "name": "X"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "artist" in resp.data

    def test_rejects_track_from_other_workspace(
        self, client_for, owner, workspace, other_workspace, make_artist, make_track
    ):
        artist = make_artist(workspace)
        foreign_artist = make_artist(other_workspace, "Foreign", "foreign")
        foreign_track = make_track(other_workspace, foreign_artist, "FT", "ft")
        resp = client_for(owner).post(
            CAMPAIGNS_URL,
            {
                "artist": str(artist.id),
                "track": str(foreign_track.id),
                "name": "Bad",
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "track" in resp.data

    def test_list_only_own_workspace_campaigns(
        self, client_for, owner, workspace, other_owner, other_workspace, make_artist
    ):
        a1 = make_artist(workspace, "Mine", "mine")
        a2 = make_artist(other_workspace, "Theirs", "theirs")
        client_for(owner).post(
            CAMPAIGNS_URL, {"artist": str(a1.id), "name": "Mine C"},
            format="json", **ws_header(workspace),
        )
        client_for(other_owner).post(
            CAMPAIGNS_URL, {"artist": str(a2.id), "name": "Their C"},
            format="json", **ws_header(other_workspace),
        )
        resp = client_for(owner).get(CAMPAIGNS_URL, **ws_header(workspace))
        names = {c["name"] for c in _results(resp)}
        assert names == {"Mine C"}

    def test_non_member_cannot_list(self, client_for, make_user, workspace):
        outsider = make_user("outsider@example.com")
        resp = client_for(outsider).get(CAMPAIGNS_URL, **ws_header(workspace))
        assert resp.status_code == 403


@pytest.mark.django_db
class TestCampaignTracksAndGoals:
    def _campaign(self, client, workspace, artist):
        return client.post(
            CAMPAIGNS_URL, {"artist": str(artist.id), "name": "C"},
            format="json", **ws_header(workspace),
        ).data["id"]

    def test_add_multiple_tracks_but_no_duplicate(
        self, client_for, owner, workspace, make_artist, make_track
    ):
        client = client_for(owner)
        artist = make_artist(workspace)
        campaign_id = self._campaign(client, workspace, artist)
        t1 = make_track(workspace, artist, "T1", "t1")
        t2 = make_track(workspace, artist, "T2", "t2")

        r1 = client.post(
            TRACKS_URL,
            {"campaign": campaign_id, "track": str(t1.id), "role": "primary"},
            format="json", **ws_header(workspace),
        )
        r2 = client.post(
            TRACKS_URL,
            {"campaign": campaign_id, "track": str(t2.id), "role": "secondary"},
            format="json", **ws_header(workspace),
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert CampaignTrack.objects.filter(campaign_id=campaign_id).count() == 2

        # Duplicate (same campaign + track) is rejected.
        dup = client.post(
            TRACKS_URL,
            {"campaign": campaign_id, "track": str(t1.id)},
            format="json", **ws_header(workspace),
        )
        assert dup.status_code == 400

    def test_create_goal(self, client_for, owner, workspace, make_artist):
        client = client_for(owner)
        artist = make_artist(workspace)
        campaign_id = self._campaign(client, workspace, artist)
        resp = client.post(
            GOALS_URL,
            {
                "campaign": campaign_id,
                "goal_type": "views",
                "target_value": "100000",
                "unit": "views",
            },
            format="json", **ws_header(workspace),
        )
        assert resp.status_code == 201
        goal = CampaignGoal.objects.get(id=resp.data["id"])
        assert goal.workspace_id == workspace.id
        assert goal.goal_type == "views"


@pytest.mark.django_db
class TestCampaignFilters:
    def test_filter_by_status(self, client_for, owner, workspace, make_artist):
        client = client_for(owner)
        artist = make_artist(workspace)
        client.post(
            CAMPAIGNS_URL,
            {"artist": str(artist.id), "name": "Active C", "status": "active"},
            format="json", **ws_header(workspace),
        )
        client.post(
            CAMPAIGNS_URL,
            {"artist": str(artist.id), "name": "Draft C", "status": "draft"},
            format="json", **ws_header(workspace),
        )
        resp = client.get(f"{CAMPAIGNS_URL}?status=active", **ws_header(workspace))
        names = {c["name"] for c in _results(resp)}
        assert names == {"Active C"}
