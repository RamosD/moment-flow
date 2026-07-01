"""CRUD, slug uniqueness, isolation and YouTube link tests."""

import pytest

from apps.catalogue.models import Artist, Track, TrackPlatformLink
from apps.catalogue.tests.conftest import ws_header

ARTISTS_URL = "/api/v1/artists/"
TRACKS_URL = "/api/v1/tracks/"
LINKS_URL = "/api/v1/track-platform-links/"
VIDEO_ID = "dQw4w9WgXcQ"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def _create_artist(client, workspace, name="Test Artist"):
    return client.post(
        ARTISTS_URL, {"name": name}, format="json", **ws_header(workspace)
    )


def _create_track(client, workspace, artist_id, title="Test Track"):
    return client.post(
        TRACKS_URL,
        {"artist": str(artist_id), "title": title},
        format="json",
        **ws_header(workspace),
    )


@pytest.mark.django_db
class TestArtistCrud:
    def test_owner_creates_artist(self, client_for, owner, workspace):
        resp = _create_artist(client_for(owner), workspace, "Daft Punk")
        assert resp.status_code == 201
        assert resp.data["slug"] == "daft-punk"
        artist = Artist.objects.get(id=resp.data["id"])
        assert artist.workspace_id == workspace.id
        assert artist.created_by_id == owner.id
        assert artist.status == Artist.Status.ACTIVE

    def test_slug_unique_per_workspace_but_shared_across_workspaces(
        self, client_for, owner, workspace, other_owner, other_workspace
    ):
        c1 = client_for(owner)
        first = _create_artist(c1, workspace, "Clash")
        second = _create_artist(c1, workspace, "Clash")
        assert first.data["slug"] == "clash"
        assert second.data["slug"] == "clash-2"

        # Same slug is allowed in a different workspace.
        other = _create_artist(client_for(other_owner), other_workspace, "Clash")
        assert other.data["slug"] == "clash"


@pytest.mark.django_db
class TestTrackCrud:
    def test_create_track_with_artist_in_same_workspace(
        self, client_for, owner, workspace
    ):
        client = client_for(owner)
        artist_id = _create_artist(client, workspace).data["id"]
        resp = _create_track(client, workspace, artist_id, "Hit Song")
        assert resp.status_code == 201
        assert resp.data["slug"] == "hit-song"
        track = Track.objects.get(id=resp.data["id"])
        assert track.workspace_id == workspace.id
        assert str(track.artist_id) == str(artist_id)

    def test_track_rejects_artist_from_other_workspace(
        self, client_for, owner, workspace, other_owner, other_workspace
    ):
        foreign_artist = _create_artist(
            client_for(other_owner), other_workspace, "Foreign"
        ).data["id"]
        resp = _create_track(client_for(owner), workspace, foreign_artist, "X")
        assert resp.status_code == 400
        assert "artist" in resp.data


@pytest.mark.django_db
class TestYouTubeLink:
    def _setup_track(self, client, workspace):
        artist_id = _create_artist(client, workspace).data["id"]
        return _create_track(client, workspace, artist_id).data["id"]

    def test_youtube_link_extracts_external_id(self, client_for, owner, workspace):
        client = client_for(owner)
        track_id = self._setup_track(client, workspace)
        resp = client.post(
            LINKS_URL,
            {
                "track": str(track_id),
                "platform": "youtube",
                "url": f"https://www.youtube.com/watch?v={VIDEO_ID}",
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        assert resp.data["external_id"] == VIDEO_ID
        link = TrackPlatformLink.objects.get(id=resp.data["id"])
        assert link.workspace_id == workspace.id
        assert link.external_id == VIDEO_ID

    def test_unrecognized_youtube_url_is_rejected(self, client_for, owner, workspace):
        client = client_for(owner)
        track_id = self._setup_track(client, workspace)
        resp = client.post(
            LINKS_URL,
            {
                "track": str(track_id),
                "platform": "youtube",
                "url": "https://example.com/not-youtube",
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "url" in resp.data


@pytest.mark.django_db
class TestWorkspaceIsolation:
    def test_list_returns_only_own_workspace_artists(
        self, client_for, owner, workspace, other_owner, other_workspace
    ):
        _create_artist(client_for(owner), workspace, "Mine")
        _create_artist(client_for(other_owner), other_workspace, "Theirs")

        resp = client_for(owner).get(ARTISTS_URL, **ws_header(workspace))
        names = {a["name"] for a in _results(resp)}
        assert names == {"Mine"}

    def test_non_member_cannot_list_artists(
        self, client_for, make_user, workspace
    ):
        outsider = make_user("outsider@example.com")
        resp = client_for(outsider).get(ARTISTS_URL, **ws_header(workspace))
        assert resp.status_code == 403
