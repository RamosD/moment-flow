"""Notifications: creation, listing, mark-read, broadcasts, isolation, access."""

import pytest

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.notifications.tests.conftest import ws_header

NOTIFICATIONS_URL = "/api/v1/notifications/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestNotificationListing:
    def test_create_and_list(self, client_for, owner, workspace):
        create_notification(
            workspace=workspace,
            user=owner,
            title="Report ready",
            notification_type=Notification.NotificationType.REPORT_READY,
        )
        resp = client_for(owner).get(NOTIFICATIONS_URL, **ws_header(workspace))
        assert resp.status_code == 200
        rows = _results(resp)
        assert len(rows) == 1
        assert rows[0]["title"] == "Report ready"
        assert rows[0]["status"] == "unread"

    def test_workspace_broadcast_visible_to_member(
        self, client_for, make_user, workspace, add_member
    ):
        member = make_user("member@example.com")
        add_member(workspace, member, "viewer")
        # user=None → workspace-wide broadcast.
        create_notification(workspace=workspace, title="Maintenance tonight")
        resp = client_for(member).get(NOTIFICATIONS_URL, **ws_header(workspace))
        assert resp.status_code == 200
        assert len(_results(resp)) == 1

    def test_user_directed_not_visible_to_other_member(
        self, client_for, owner, make_user, workspace, add_member
    ):
        other = make_user("member2@example.com")
        add_member(workspace, other, "viewer")
        create_notification(workspace=workspace, user=owner, title="Only for owner")
        resp = client_for(other).get(NOTIFICATIONS_URL, **ws_header(workspace))
        assert resp.status_code == 200
        assert _results(resp) == []


@pytest.mark.django_db
class TestMarkRead:
    def test_mark_single_as_read(self, client_for, owner, workspace):
        notification = create_notification(
            workspace=workspace, user=owner, title="N"
        )
        resp = client_for(owner).post(
            f"{NOTIFICATIONS_URL}{notification.id}/read/", **ws_header(workspace)
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "read"
        notification.refresh_from_db()
        assert notification.status == Notification.Status.READ
        assert notification.read_at is not None

    def test_mark_all_as_read(self, client_for, owner, workspace):
        for i in range(3):
            create_notification(workspace=workspace, user=owner, title=f"N{i}")
        resp = client_for(owner).post(
            f"{NOTIFICATIONS_URL}read-all/", **ws_header(workspace)
        )
        assert resp.status_code == 200
        assert resp.data["updated"] == 3
        assert not Notification.objects.filter(
            workspace=workspace, status=Notification.Status.UNREAD
        ).exists()


@pytest.mark.django_db
class TestNotificationAccess:
    def test_isolated_per_workspace(
        self, client_for, owner, workspace, other_owner, other_workspace
    ):
        create_notification(workspace=workspace, user=owner, title="N")
        resp = client_for(other_owner).get(
            NOTIFICATIONS_URL, **ws_header(other_workspace)
        )
        assert resp.status_code == 200
        assert _results(resp) == []

    def test_non_member_is_blocked(self, client_for, other_owner, workspace):
        resp = client_for(other_owner).get(NOTIFICATIONS_URL, **ws_header(workspace))
        assert resp.status_code == 403
