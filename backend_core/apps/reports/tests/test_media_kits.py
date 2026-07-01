"""MediaKit and MediaKitItem: creation, items, usage, isolation, permissions."""

import pytest

from apps.billing.models import UsageEvent
from apps.reports.models import MediaKit, MediaKitItem
from apps.reports.tests.conftest import ws_header

KITS_URL = "/api/v1/media-kits/"
ITEMS_URL = "/api/v1/media-kit-items/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestMediaKitCreation:
    def test_create_media_kit_for_artist(
        self, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        resp = client_for(owner).post(
            KITS_URL,
            {"artist": str(artist.id), "title": "Press Kit"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        kit = MediaKit.objects.get(id=resp.data["id"])
        assert kit.artist_id == artist.id
        assert kit.workspace_id == workspace.id
        assert kit.created_by_id == owner.id
        assert kit.status == MediaKit.Status.DRAFT

    def test_create_records_usage_event(self, client_for, owner, workspace, make_artist):
        artist = make_artist(workspace)
        client_for(owner).post(
            KITS_URL,
            {"artist": str(artist.id), "title": "K"},
            format="json",
            **ws_header(workspace),
        )
        assert UsageEvent.objects.filter(
            workspace=workspace, event_type=UsageEvent.EventType.MEDIA_KIT_GENERATED
        ).exists()

    def test_rejects_artist_from_other_workspace(
        self, client_for, owner, workspace, other_workspace, make_artist
    ):
        foreign = make_artist(other_workspace, name="F", slug="f")
        resp = client_for(owner).post(
            KITS_URL,
            {"artist": str(foreign.id), "title": "K"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 400
        assert "artist" in resp.data


@pytest.mark.django_db
class TestMediaKitItems:
    def test_media_kit_can_have_items(self, client_for, owner, workspace, make_artist):
        artist = make_artist(workspace)
        kit = MediaKit.objects.create(
            workspace=workspace, artist=artist, title="K"
        )
        resp = client_for(owner).post(
            ITEMS_URL,
            {
                "media_kit": str(kit.id),
                "item_type": "bio",
                "title": "Short bio",
                "content": "An artist.",
                "sort_order": 0,
            },
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 201
        item = MediaKitItem.objects.get(id=resp.data["id"])
        assert item.media_kit_id == kit.id
        assert item.workspace_id == workspace.id

    def test_items_nested_in_media_kit_payload(
        self, client_for, owner, workspace, make_artist
    ):
        artist = make_artist(workspace)
        kit = MediaKit.objects.create(workspace=workspace, artist=artist, title="K")
        MediaKitItem.objects.create(
            workspace=workspace, media_kit=kit, item_type="stats", title="Stats"
        )
        resp = client_for(owner).get(f"{KITS_URL}{kit.id}/", **ws_header(workspace))
        assert resp.status_code == 200
        assert len(resp.data["items"]) == 1


@pytest.mark.django_db
class TestMediaKitIsolationAndPermissions:
    def test_media_kits_isolated_per_workspace(
        self, client_for, owner, workspace, other_owner, other_workspace, make_artist
    ):
        artist = make_artist(workspace)
        MediaKit.objects.create(workspace=workspace, artist=artist, title="K")
        resp = client_for(other_owner).get(KITS_URL, **ws_header(other_workspace))
        assert resp.status_code == 200
        assert _results(resp) == []

    def test_viewer_cannot_generate(
        self, client_for, make_user, workspace, add_member, make_artist
    ):
        viewer = make_user("viewer@example.com")
        add_member(workspace, viewer, "viewer")
        artist = make_artist(workspace)
        resp = client_for(viewer).post(
            KITS_URL,
            {"artist": str(artist.id), "title": "K"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == 403
