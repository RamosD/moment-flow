"""Plan/feature seeding and the public plan catalogue API."""

import pytest

from apps.billing.models import Plan, PlanFeature
from apps.billing.tests.conftest import ws_header

PLANS_URL = "/api/v1/plans/"

EXPECTED_PLAN_KEYS = {
    "trial",
    "artist_starter",
    "artist_growth",
    "manager",
    "label_agency",
    "white_label",
    "enterprise",
}


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestPlanSeed:
    def test_seed_creates_all_plans(self, seeded):
        assert seeded["plans"] == len(EXPECTED_PLAN_KEYS)
        assert set(Plan.objects.values_list("plan_key", flat=True)) == EXPECTED_PLAN_KEYS

    def test_features_have_limits_and_flags(self, seeded):
        starter = Plan.objects.get(plan_key="artist_starter")
        tracks = PlanFeature.objects.get(plan=starter, feature_key="tracks_limit")
        assert tracks.limit_value == 15
        assert tracks.is_enabled is True

        watermark = PlanFeature.objects.get(
            plan=starter, feature_key="watermark_removal"
        )
        assert watermark.is_enabled is False

    def test_enterprise_features_are_unlimited(self, seeded):
        enterprise = Plan.objects.get(plan_key="enterprise")
        artists = PlanFeature.objects.get(plan=enterprise, feature_key="artists_limit")
        assert artists.limit_value is None  # unlimited
        assert artists.is_enabled is True

    def test_seed_is_idempotent(self, seeded):
        from apps.billing.seeds import seed_billing

        before = PlanFeature.objects.count()
        seed_billing()
        assert PlanFeature.objects.count() == before


@pytest.mark.django_db
class TestPublicPlanAPI:
    def test_lists_only_public_active_plans(self, client_for, owner, workspace):
        resp = client_for(owner).get(PLANS_URL, **ws_header(workspace))
        assert resp.status_code == 200
        keys = {row["plan_key"] for row in _results(resp)}
        # white_label and enterprise are not public.
        assert keys == EXPECTED_PLAN_KEYS - {"white_label", "enterprise"}

    def test_plan_payload_includes_features(self, client_for, owner, workspace):
        resp = client_for(owner).get(PLANS_URL, **ws_header(workspace))
        starter = next(r for r in _results(resp) if r["plan_key"] == "artist_starter")
        feature_keys = {f["feature_key"] for f in starter["features"]}
        assert "artists_limit" in feature_keys
        assert "storage_gb" in feature_keys

    def test_anonymous_is_rejected(self, seeded):
        from rest_framework.test import APIClient

        resp = APIClient().get(PLANS_URL)
        assert resp.status_code == 401
