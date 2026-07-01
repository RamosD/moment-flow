"""API tests for workspace creation, isolation and X-Workspace-ID resolution."""

import uuid

import pytest

from apps.workspaces.models import ROLE_OWNER, Workspace, WorkspaceMember

WORKSPACES_URL = "/api/v1/workspaces/"
CURRENT_URL = "/api/v1/workspaces/current/"
HEADER = "X-Workspace-ID"


def _results(response):
    """Return the list of items whether or not pagination is enabled."""
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestWorkspaceCreation:
    def test_authenticated_user_creates_workspace(self, client_a):
        response = client_a.post(
            WORKSPACES_URL, {"name": "Alice Records"}, format="json"
        )
        assert response.status_code == 201
        assert response.data["name"] == "Alice Records"
        assert response.data["slug"] == "alice-records"
        # status defaults to trial and created_by is set server-side.
        assert response.data["status"] == Workspace.Status.TRIAL

    def test_anonymous_cannot_create_workspace(self):
        from rest_framework.test import APIClient

        response = APIClient().post(
            WORKSPACES_URL, {"name": "Nope"}, format="json"
        )
        assert response.status_code == 401

    def test_creator_becomes_active_owner_member(self, client_a, user_a):
        response = client_a.post(
            WORKSPACES_URL, {"name": "Alice Records"}, format="json"
        )
        workspace = Workspace.objects.get(id=response.data["id"])
        member = WorkspaceMember.objects.get(workspace=workspace, user=user_a)
        assert member.role_key == ROLE_OWNER
        assert member.status == WorkspaceMember.Status.ACTIVE
        assert member.joined_at is not None
        assert member.invited_by_id == user_a.id

    def test_slug_is_unique_across_same_name(self, client_a):
        first = client_a.post(WORKSPACES_URL, {"name": "Studio"}, format="json")
        second = client_a.post(WORKSPACES_URL, {"name": "Studio"}, format="json")
        assert first.data["slug"] == "studio"
        assert second.data["slug"] == "studio-2"


@pytest.mark.django_db
class TestWorkspaceIsolation:
    def test_user_lists_only_own_workspaces(self, client_a, client_b):
        client_a.post(WORKSPACES_URL, {"name": "Alice WS"}, format="json")
        client_b.post(WORKSPACES_URL, {"name": "Bob WS"}, format="json")

        resp_a = client_a.get(WORKSPACES_URL)
        names_a = {w["name"] for w in _results(resp_a)}
        assert names_a == {"Alice WS"}

        resp_b = client_b.get(WORKSPACES_URL)
        names_b = {w["name"] for w in _results(resp_b)}
        assert names_b == {"Bob WS"}

    def test_user_cannot_retrieve_other_workspace(self, client_a, client_b):
        created = client_a.post(
            WORKSPACES_URL, {"name": "Alice WS"}, format="json"
        )
        ws_id = created.data["id"]
        # Bob is not a member -> not found in his scoped queryset.
        resp = client_b.get(f"{WORKSPACES_URL}{ws_id}/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestWorkspaceContextHeader:
    def _create(self, client):
        return client.post(
            WORKSPACES_URL, {"name": "Context WS"}, format="json"
        ).data["id"]

    def test_valid_header_resolves_current_workspace(self, client_a):
        ws_id = self._create(client_a)
        resp = client_a.get(CURRENT_URL, **{f"HTTP_{HEADER.upper().replace('-', '_')}": ws_id})
        assert resp.status_code == 200
        assert resp.data["id"] == ws_id

    def test_missing_header_is_rejected(self, client_a):
        self._create(client_a)
        resp = client_a.get(CURRENT_URL)
        assert resp.status_code == 400

    def test_malformed_header_is_rejected(self, client_a):
        self._create(client_a)
        resp = client_a.get(
            CURRENT_URL, **{f"HTTP_{HEADER.upper().replace('-', '_')}": "not-a-uuid"}
        )
        assert resp.status_code == 400

    def test_non_member_workspace_is_rejected(self, client_a, client_b):
        ws_id = self._create(client_a)
        # Bob presents Alice's workspace id -> forbidden.
        resp = client_b.get(
            CURRENT_URL, **{f"HTTP_{HEADER.upper().replace('-', '_')}": ws_id}
        )
        assert resp.status_code == 403

    def test_unknown_workspace_is_rejected(self, client_a):
        self._create(client_a)
        resp = client_a.get(
            CURRENT_URL,
            **{f"HTTP_{HEADER.upper().replace('-', '_')}": str(uuid.uuid4())},
        )
        assert resp.status_code == 403
