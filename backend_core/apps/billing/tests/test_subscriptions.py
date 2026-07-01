"""Subscriptions: services and the active-subscription endpoint."""

import pytest

from apps.billing.models import Subscription
from apps.billing.services import (
    get_active_subscription,
    get_plan_limit,
    workspace_has_feature,
)
from apps.billing.tests.conftest import ws_header

SUBSCRIPTION_URL = "/api/v1/billing/subscription/"


@pytest.mark.django_db
class TestSubscriptionServices:
    def test_get_active_subscription(self, workspace, subscribe):
        sub = subscribe(workspace, "artist_starter")
        assert get_active_subscription(workspace) == sub

    def test_cancelled_subscription_is_not_active(self, workspace, subscribe):
        subscribe(workspace, "artist_starter", status=Subscription.Status.CANCELLED)
        assert get_active_subscription(workspace) is None

    def test_trialing_is_active(self, workspace, subscribe):
        subscribe(workspace, "trial", status=Subscription.Status.TRIALING)
        assert get_active_subscription(workspace) is not None

    def test_workspace_has_feature(self, workspace, subscribe):
        subscribe(workspace, "artist_starter")
        assert workspace_has_feature(workspace, "artists_limit") is True
        # disabled on the starter plan
        assert workspace_has_feature(workspace, "watermark_removal") is False

    def test_get_plan_limit(self, workspace, subscribe):
        subscribe(workspace, "artist_starter")
        assert get_plan_limit(workspace, "tracks_limit") == 15

    def test_no_subscription_has_no_limit(self, workspace):
        assert get_plan_limit(workspace, "tracks_limit") is None
        assert workspace_has_feature(workspace, "tracks_limit") is False


@pytest.mark.django_db
class TestActiveSubscriptionAPI:
    def test_returns_active_subscription(
        self, client_for, owner, workspace, subscribe
    ):
        subscribe(workspace, "artist_growth")
        resp = client_for(owner).get(SUBSCRIPTION_URL, **ws_header(workspace))
        assert resp.status_code == 200
        assert resp.data["plan"]["plan_key"] == "artist_growth"
        assert resp.data["status"] == "active"

    def test_returns_null_without_subscription(self, client_for, owner, workspace):
        resp = client_for(owner).get(SUBSCRIPTION_URL, **ws_header(workspace))
        assert resp.status_code == 200
        assert resp.data["subscription"] is None

    def test_isolation_other_workspace_subscription_hidden(
        self, client_for, owner, workspace, other_workspace, subscribe
    ):
        subscribe(other_workspace, "manager")
        resp = client_for(owner).get(SUBSCRIPTION_URL, **ws_header(workspace))
        # owner is not a member of other_workspace; their own workspace has none.
        assert resp.status_code == 200
        assert resp.data["subscription"] is None
