"""Unit tests for ScoringEngine (IE-005).

Each test drives the engine directly (no HTTP) and asserts deterministic,
explainable behaviour for one rule, composite or edge case. The scenarios map
to the acceptance criteria: good signals, weak signals, insufficient data,
partial data, and the 0/100 limits.
"""

from app.schemas.scoring import ScoringRequest
from app.services.scoring_engine import ScoringEngine, _grade_for

service = ScoringEngine()


def _request(data: dict | None = None, context: dict | None = None) -> ScoringRequest:
    return ScoringRequest(
        payload_version="1.0",
        workspace_id="ws-1",
        request_id="req-1",
        entity={"type": "campaign", "id": "campaign-1"},
        context=context or {},
        data=data or {},
    )


def _score(data: dict | None = None, context: dict | None = None):
    return service.score(_request(data, context))


def _scores(response) -> dict:
    return response.result.scores.model_dump()


def _explanation_codes(response) -> set[str]:
    return {explanation.code for explanation in response.explanations}


def _warning_codes(response) -> set[str]:
    return {warning.code for warning in response.warnings}


REF = {"reference_date": "2026-06-24"}


# --- Scenario 1: good signals --------------------------------------------------

GOOD_DATA = {
    "campaign": {
        "status": "active",
        "primary_goal": "grow streams",
        "start_date": "2026-06-01",
        "end_date": "2026-12-31",
    },
    "artist": {"name": "Nova"},
    "track": {"title": "Hit", "release_date": "2026-06-20"},
    "smart_link_stats": {
        "total_clicks": 2000,
        "clicks_last_7_days": 120,
        "clicks_last_30_days": 500,
        "active_links": 4,
    },
    "content_outputs": [
        {"status": "completed", "created_at": "2026-06-20"},
        {"status": "completed", "created_at": "2026-06-22"},
    ],
    "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
    "media_kits": [{"status": "published"}],
}


def test_good_campaign_scores_strongly_and_grades_a() -> None:
    response = _score(GOOD_DATA, REF)
    scores = _scores(response)

    assert scores["campaign_readiness_score"] == 100
    assert scores["momentum_score"] == 100
    assert scores["risk_score"] == 0
    # All gaps filled, but the track is inside its release window → some upside.
    assert scores["content_opportunity_score"] == 25
    assert scores["priority_score"] is not None
    assert response.result.grade == "A"


def test_good_campaign_has_an_explanation_per_score() -> None:
    response = _score(GOOD_DATA, REF)
    codes = _explanation_codes(response)

    for score_code in (
        "campaign_readiness_score",
        "momentum_score",
        "content_opportunity_score",
        "risk_score",
        "priority_score",
        "grade",
    ):
        assert score_code in codes
    # No "unknown" warnings when everything is computable.
    assert not any(code.endswith("_unknown") for code in _warning_codes(response))


# --- Scenario 2: weak signals --------------------------------------------------


def test_weak_campaign_low_momentum_high_opportunity_poor_grade() -> None:
    response = _score(
        {
            "campaign": {"status": "active", "start_date": "2026-06-01", "end_date": "2026-12-31"},
            "smart_link_stats": {
                "total_clicks": 5,
                "clicks_last_7_days": 0,
                "clicks_last_30_days": 2,
                "active_links": 1,
            },
        },
        REF,
    )
    scores = _scores(response)

    assert all(scores[key] is not None for key in scores)
    assert scores["momentum_score"] <= 10
    assert scores["content_opportunity_score"] >= 80
    assert 30 <= scores["campaign_readiness_score"] <= 45
    assert response.result.grade in {"C", "D"}


# --- Scenario 3: insufficient data ---------------------------------------------


def test_empty_bundle_yields_all_null_and_unknown_grade() -> None:
    response = _score({})
    scores = _scores(response)

    assert all(value is None for value in scores.values())
    assert response.result.grade == "unknown"
    assert response.status == "completed"  # not an error envelope

    warnings = _warning_codes(response)
    assert "insufficient_data" in warnings
    for score_code in (
        "campaign_readiness_score",
        "momentum_score",
        "content_opportunity_score",
        "risk_score",
        "priority_score",
        "grade",
    ):
        assert f"{score_code}_unknown" in warnings


# --- Scenario 4: partial data --------------------------------------------------


def test_partial_data_computes_what_it_can_and_nulls_the_rest() -> None:
    # Campaign identity but no analytics: momentum cannot be computed.
    response = _score(
        {"campaign": {"status": "active", "start_date": "2026-07-01"}, "artist": {"name": "X"}},
        REF,
    )
    scores = _scores(response)

    assert scores["momentum_score"] is None
    assert "momentum_score_unknown" in _warning_codes(response)
    # Readiness/opportunity/risk are computable from the campaign object alone.
    assert scores["campaign_readiness_score"] is not None
    assert scores["content_opportunity_score"] is not None
    assert scores["risk_score"] is not None
    # Two+ components available → priority is still computed.
    assert scores["priority_score"] is not None
    assert response.result.grade != "unknown"
    assert "insufficient_data" not in _warning_codes(response)


# --- Scenario 5: limits (0 and 100) --------------------------------------------


def test_readiness_reaches_100() -> None:
    response = _score(
        {
            "campaign": {"status": "active", "primary_goal": "g", "start_date": "2026-01-01"},
            "artist": {"name": "A"},
            "track": {"title": "T"},
            "media_kits": [{"status": "published"}],
        }
    )
    assert _scores(response)["campaign_readiness_score"] == 100


def test_readiness_floor_is_0() -> None:
    response = _score({"campaign": {"status": "not-a-real-status"}})
    assert _scores(response)["campaign_readiness_score"] == 0


def test_momentum_reaches_100() -> None:
    response = _score(
        {
            "smart_link_stats": {
                "total_clicks": 2000,
                "clicks_last_7_days": 100,
                "clicks_last_30_days": 400,
                "active_links": 5,
            },
            "content_outputs": [
                {"status": "completed", "created_at": "2026-06-20"},
                {"status": "completed", "created_at": "2026-06-21"},
            ],
        },
        REF,
    )
    assert _scores(response)["momentum_score"] == 100


def test_momentum_floor_is_0() -> None:
    response = _score(
        {
            "smart_link_stats": {
                "total_clicks": 0,
                "clicks_last_7_days": 0,
                "clicks_last_30_days": 0,
                "active_links": 0,
            }
        }
    )
    assert _scores(response)["momentum_score"] == 0


def test_content_opportunity_reaches_100() -> None:
    response = _score(
        {"campaign": {"status": "active"}, "track": {"release_date": "2026-06-24"}},
        REF,
    )
    assert _scores(response)["content_opportunity_score"] == 100


def test_content_opportunity_floor_is_0() -> None:
    response = _score(
        {
            "campaign": {"status": "completed"},
            "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
            "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
            "media_kits": [{"status": "published"}],
        },
        REF,
    )
    assert _scores(response)["content_opportunity_score"] == 0


def test_risk_reaches_100() -> None:
    response = _score(
        {
            # active + overdue + inconsistent dates + negative (→ zero) stats.
            "campaign": {"status": "active", "start_date": "2026-06-10", "end_date": "2026-06-01"},
            "smart_link_stats": {"total_clicks": -5, "clicks_last_7_days": -1, "active_links": -1},
        },
        REF,
    )
    assert _scores(response)["risk_score"] == 100


def test_risk_floor_is_0() -> None:
    response = _score(
        {
            "campaign": {"status": "draft", "start_date": "2026-01-01", "end_date": "2026-12-31"},
            "content_outputs": [{"status": "completed"}],
            "smart_link_stats": {"total_clicks": 500, "clicks_last_7_days": 30},
        },
        REF,
    )
    assert _scores(response)["risk_score"] == 0


def test_all_scores_stay_within_bounds() -> None:
    response = _score(GOOD_DATA, REF)
    for value in _scores(response).values():
        assert value is None or 0 <= value <= 100


# --- priority composite + renormalisation --------------------------------------


def test_priority_blends_available_scores() -> None:
    value, explanation, warning = service._priority(72, 64, 81, 28)

    # 0.35*81 + 0.25*64 + 0.20*28 + 0.20*72 = 64.35 → 64
    assert value == 64
    assert warning is None
    assert explanation is not None and explanation.code == "priority_score"


def test_priority_renormalises_over_available_scores() -> None:
    # Only momentum (64) and opportunity (80) present.
    # (0.25*64 + 0.35*80) / 0.60 = 73.33 → 73
    value, _explanation, warning = service._priority(None, 64, 80, None)

    assert value == 73
    assert warning is None


def test_priority_is_unknown_with_fewer_than_two_components() -> None:
    value, explanation, warning = service._priority(None, None, 80, None)

    assert value is None
    assert explanation is None
    assert warning is not None and warning.code == "priority_score_unknown"


# --- grade thresholds ----------------------------------------------------------


def test_grade_thresholds_are_stable() -> None:
    assert _grade_for(100) == "A"
    assert _grade_for(80) == "A"
    assert _grade_for(79) == "B"
    assert _grade_for(65) == "B"
    assert _grade_for(64) == "C"
    assert _grade_for(45) == "C"
    assert _grade_for(44) == "D"
    assert _grade_for(0) == "D"


# --- consistency checks: warn, never raise -------------------------------------


def test_negative_smart_link_stats_warn_and_do_not_raise() -> None:
    response = _score(
        {"campaign": {"status": "active"}, "smart_link_stats": {"total_clicks": -10}},
        REF,
    )
    assert "negative_smart_link_stats" in _warning_codes(response)
    assert response.status == "completed"


def test_inconsistent_campaign_dates_warn() -> None:
    response = _score(
        {"campaign": {"status": "active", "start_date": "2026-06-10", "end_date": "2026-06-01"}},
        REF,
    )
    assert "inconsistent_campaign_dates" in _warning_codes(response)


def test_future_content_output_warns() -> None:
    response = _score(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-12-31"}],
        },
        REF,
    )
    assert "future_content_output_date" in _warning_codes(response)


def test_invalid_reference_date_warns_and_does_not_raise() -> None:
    response = _score({"campaign": {"status": "active"}}, {"reference_date": "31-12-2026"})

    assert "invalid_reference_date" in _warning_codes(response)
    assert response.status == "completed"


def test_unknown_extra_fields_are_tolerated() -> None:
    response = _score({"campaign": {"status": "active", "future_field": "kept"}, "extra": {"x": 1}})
    assert response.status == "completed"


# --- determinism ---------------------------------------------------------------


def test_same_input_produces_identical_output() -> None:
    first = service.score(_request(GOOD_DATA, REF)).model_dump()
    second = service.score(_request(GOOD_DATA, REF)).model_dump()

    assert first == second


def test_recency_degrades_to_presence_without_reference_date() -> None:
    # Without a reference date the engine must not read the wall clock; the
    # recent-content component falls back to a presence-based value.
    with_ref = _scores(_score(GOOD_DATA, REF))
    without_ref = _scores(_score(GOOD_DATA))

    # Still deterministic and bounded; momentum may differ (recency unknown).
    assert without_ref["momentum_score"] is not None
    assert with_ref["momentum_score"] >= without_ref["momentum_score"]


def test_metadata_echoes_payload_version_without_timestamp() -> None:
    response = _score({"campaign": {"status": "active"}})

    assert response.metadata.payload_version == "1.0"
    assert response.metadata.generated_at is None
