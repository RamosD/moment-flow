"""RBAC boundaries per role: viewer, editor, admin, owner, billing_admin.

Two gates are exercised: creating an artist (needs ``artists:create``) and reading
billing (needs ``billing:view``). Expectations follow the seeded role definitions
in ``apps.rbac.seeds`` — permissions are never relaxed to make a test pass.
"""

import pytest

from tests import factories
from tests.conftest import ws_header

ARTISTS_URL = "/api/v1/artists/"
CREDITS_URL = "/api/v1/billing/credits/"


@pytest.fixture
def workspace_with(db, seeded, add_member):
    """Create a workspace and a member holding ``role_key``; return (ws, user)."""

    def _factory(role_key):
        workspace = factories.WorkspaceFactory()
        user = factories.UserFactory()
        add_member(workspace, user, role_key)
        return workspace, user

    return _factory


@pytest.mark.django_db
class TestArtistCreationPermission:
    # artists:create is held by editor/admin/owner, not viewer/billing_admin.
    @pytest.mark.parametrize(
        "role_key,expected",
        [
            ("viewer", 403),
            ("editor", 201),
            ("admin", 201),
            ("owner", 201),
            ("billing_admin", 403),
        ],
    )
    def test_create_artist(self, role_key, expected, workspace_with, auth_client):
        workspace, user = workspace_with(role_key)
        resp = auth_client(user).post(
            ARTISTS_URL,
            {"name": f"Artist for {role_key}"},
            format="json",
            **ws_header(workspace),
        )
        assert resp.status_code == expected


@pytest.mark.django_db
class TestBillingViewPermission:
    # billing:view is held by admin/owner/billing_admin, not viewer/editor.
    @pytest.mark.parametrize(
        "role_key,expected",
        [
            ("viewer", 403),
            ("editor", 403),
            ("admin", 200),
            ("owner", 200),
            ("billing_admin", 200),
        ],
    )
    def test_view_billing_credits(self, role_key, expected, workspace_with, auth_client):
        workspace, user = workspace_with(role_key)
        resp = auth_client(user).get(CREDITS_URL, **ws_header(workspace))
        assert resp.status_code == expected


@pytest.mark.django_db
class TestViewerIsReadOnly:
    def test_viewer_can_list_but_not_create(self, workspace_with, auth_client):
        workspace, user = workspace_with("viewer")
        factories.ArtistFactory(workspace=workspace)
        client = auth_client(user)

        assert client.get(ARTISTS_URL, **ws_header(workspace)).status_code == 200
        create = client.post(
            ARTISTS_URL, {"name": "Nope"}, format="json", **ws_header(workspace)
        )
        assert create.status_code == 403
