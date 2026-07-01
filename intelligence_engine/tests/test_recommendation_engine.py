"""Unit tests for RecommendationEngine (IE-006).

Each test drives the engine directly (no HTTP) and asserts deterministic,
explainable behaviour for one rule or edge case. The engine only *suggests*
actions: every suggested pack/template is checked against the seeded product
catalogue, and no test (or the engine) ever touches Django or the renderer.
"""

from app.schemas.recommendations import Recommendation, RecommendationsRequest
from app.services.recommendation_engine import (
    SUPPORTED_PACKS,
    SUPPORTED_TEMPLATE_KEYS,
    RecommendationEngine,
)

service = RecommendationEngine()

REF = {"reference_date": "2026-06-24"}


def _request(data: dict | None = None, context: dict | None = None) -> RecommendationsRequest:
    return RecommendationsRequest(
        payload_version="1.0",
        workspace_id="ws-1",
        request_id="req-1",
        entity={"type": "campaign", "id": "campaign-1"},
        context=context or {},
        data=data or {},
    )


def _recommend(data: dict | None = None, context: dict | None = None):
    return service.recommend(_request(data, context))


def _actions(response) -> list[str]:
    return [rec.action for rec in response.result.recommendations]


def _by_action(response, action: str) -> Recommendation | None:
    return next((rec for rec in response.result.recommendations if rec.action == action), None)


def _warning_codes(response) -> set[str]:
    return {warning.code for warning in response.warnings}


# --- create_release_post -------------------------------------------------------


def test_release_window_recommends_release_post_high() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "single_release"},
            "track": {"release_date": "2026-06-20"},
        },
        REF,
    )
    rec = _by_action(response, "create_release_post")

    assert rec is not None
    assert rec.priority == "high"
    assert rec.suggested_content_pack == "release_pack"
    assert rec.expected_outputs[0].output_type == "post"
    assert any(e.code == "release_window" for e in rec.explanations)
    # Highest-priority recommendation comes first.
    assert response.result.recommendations[0].priority == "high"


def test_release_type_campaign_without_window_is_medium() -> None:
    response = _recommend(
        {"campaign": {"status": "scheduled", "campaign_type": "album_release"}}, REF
    )
    rec = _by_action(response, "create_release_post")

    assert rec is not None
    assert rec.priority == "medium"
    assert any(e.code == "release_campaign_active" for e in rec.explanations)


# --- create_milestone_post -----------------------------------------------------


def test_achieved_milestone_goal_recommends_milestone_post() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "goals": [{"goal_type": "milestone", "status": "achieved"}],
        },
        REF,
    )
    rec = _by_action(response, "create_milestone_post")

    assert rec is not None
    assert rec.priority == "high"
    assert rec.suggested_content_pack == "milestone_pack"
    assert {o.output_type for o in rec.expected_outputs} == {"post", "carousel"}
    assert any(e.code == "milestone_goal_achieved" for e in rec.explanations)


def test_milestone_click_threshold_recommends_milestone_post() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 5},
        },
        REF,
    )
    rec = _by_action(response, "create_milestone_post")

    assert rec is not None
    assert any(e.code == "milestone_click_threshold" for e in rec.explanations)


# --- create_weekly_growth_post -------------------------------------------------


def test_weekly_growth_campaign_type_recommends_weekly_post() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "weekly_growth_campaign"},
            "smart_link_stats": {"clicks_last_7_days": 50, "total_clicks": 300},
        },
        REF,
    )
    rec = _by_action(response, "create_weekly_growth_post")

    assert rec is not None
    assert rec.suggested_content_pack == "weekly_growth_pack"
    # The weekly post already includes a story → a standalone story is suppressed.
    assert "create_story" not in _actions(response)


def test_weekly_click_signal_recommends_weekly_post() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "smart_link_stats": {"clicks_last_7_days": 25, "total_clicks": 100},
        },
        REF,
    )
    rec = _by_action(response, "create_weekly_growth_post")

    assert rec is not None
    assert any(e.code == "weekly_growth_signal" for e in rec.explanations)


# --- create_media_kit ----------------------------------------------------------


def test_missing_media_kit_recommends_media_kit() -> None:
    response = _recommend(
        {"campaign": {"status": "active", "campaign_type": "media_campaign"}}, REF
    )
    rec = _by_action(response, "create_media_kit")

    assert rec is not None
    assert rec.priority == "high"  # media_campaign
    assert rec.suggested_content_pack == "auto_media_kit"
    assert rec.expected_outputs[0].output_type == "media_kit"


def test_existing_media_kit_is_not_recommended() -> None:
    response = _recommend(
        {"campaign": {"status": "active"}, "media_kits": [{"status": "published"}]}, REF
    )
    assert "create_media_kit" not in _actions(response)


def test_draft_campaign_does_not_get_media_kit() -> None:
    response = _recommend({"campaign": {"status": "draft"}}, REF)
    assert "create_media_kit" not in _actions(response)


# --- create_report -------------------------------------------------------------


def test_report_due_recommends_report() -> None:
    response = _recommend(
        {
            "campaign": {"status": "completed"},
            "content_outputs": [{"status": "completed"}],
        },
        REF,
    )
    rec = _by_action(response, "create_report")

    assert rec is not None
    assert rec.expected_outputs[0].output_type == "report"
    assert any(e.code == "report_due" for e in rec.explanations)


def test_recent_report_clears_report_recommendation() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed"}],
            "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
        },
        REF,
    )
    assert "create_report" not in _actions(response)


# --- create_story --------------------------------------------------------------


def test_active_campaign_with_activity_recommends_story() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "smart_link_stats": {"total_clicks": 50, "clicks_last_7_days": 5, "active_links": 2},
        },
        REF,
    )
    rec = _by_action(response, "create_story")

    assert rec is not None
    assert rec.priority == "low"
    assert rec.expected_outputs[0].output_type == "story"


# --- improve_smart_link --------------------------------------------------------


def test_inactive_smart_link_recommends_improvement_high_when_active() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active"},
            "smart_link_stats": {
                "total_clicks": 0,
                "clicks_last_7_days": 0,
                "clicks_last_30_days": 0,
                "active_links": 0,
            },
        },
        REF,
    )
    rec = _by_action(response, "improve_smart_link")

    assert rec is not None
    assert rec.priority == "high"
    assert rec.suggested_content_pack is None
    assert rec.expected_outputs == []
    assert any(e.code == "smart_link_inactive" for e in rec.explanations)
    assert response.result.recommendations[0].priority == "high"


# --- wait_for_more_data / no_action -------------------------------------------


def test_insufficient_data_waits_with_warning() -> None:
    response = _recommend({})

    assert _actions(response) == ["wait_for_more_data"]
    assert response.result.recommendations[0].priority == "low"
    assert "insufficient_data" in _warning_codes(response)


def test_healthy_campaign_yields_only_no_action() -> None:
    response = _recommend(
        {
            "campaign": {
                "status": "paused",
                "campaign_type": "custom",
                "start_date": "2026-06-01",
                "end_date": "2026-12-31",
                "primary_goal": "grow",
            },
            "artist": {"name": "A"},
            "track": {"title": "T", "release_date": "2026-01-01"},
            "smart_link_stats": {
                "total_clicks": 800,
                "clicks_last_7_days": 5,
                "clicks_last_30_days": 100,
                "active_links": 4,
            },
            "content_outputs": [{"status": "completed", "created_at": "2026-06-22"}],
            "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
            "media_kits": [{"status": "published"}],
        },
        REF,
    )

    assert _actions(response) == ["no_action"]
    assert "insufficient_data" not in _warning_codes(response)


# --- cross-cutting guarantees --------------------------------------------------


def test_every_recommendation_has_the_required_fields() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "single_release"},
            "track": {"release_date": "2026-06-20"},
            "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
        },
        REF,
    )
    assert response.result.recommendations
    for rec in response.result.recommendations:
        assert rec.action
        assert rec.priority in {"low", "medium", "high"}
        assert 0.0 <= rec.confidence <= 1.0
        assert rec.reason
        assert rec.explanations  # each recommendation carries its own justification


def test_suggestions_only_reference_supported_product_catalogue() -> None:
    # Drive several scenarios and assert every pack/template is fulfilment-ready.
    scenarios = [
        {
            "campaign": {"status": "active", "campaign_type": "single_release"},
            "track": {"release_date": "2026-06-20"},
        },
        {
            "campaign": {"status": "active", "campaign_type": "milestone_campaign"},
            "smart_link_stats": {"total_clicks": 1500},
        },
        {
            "campaign": {"status": "active", "campaign_type": "weekly_growth_campaign"},
            "smart_link_stats": {"clicks_last_7_days": 50},
        },
        {"campaign": {"status": "completed"}, "content_outputs": [{"status": "completed"}]},
    ]
    for data in scenarios:
        response = _recommend(data, REF)
        for rec in response.result.recommendations:
            assert (
                rec.suggested_content_pack is None or rec.suggested_content_pack in SUPPORTED_PACKS
            )
            for output in rec.expected_outputs:
                assert output.template_key is None or output.template_key in SUPPORTED_TEMPLATE_KEYS


def test_recommendations_are_sorted_by_priority() -> None:
    response = _recommend(
        {
            "campaign": {"status": "active", "campaign_type": "media_campaign"},
            "smart_link_stats": {
                "total_clicks": 0,
                "clicks_last_7_days": 0,
                "active_links": 0,
            },
        },
        REF,
    )
    ranks = [
        {"high": 0, "medium": 1, "low": 2}[r.priority] for r in response.result.recommendations
    ]
    assert ranks == sorted(ranks)


def test_negative_smart_link_stats_warn_without_raising() -> None:
    response = _recommend(
        {"campaign": {"status": "active"}, "smart_link_stats": {"total_clicks": -5}}, REF
    )
    assert "negative_smart_link_stats" in _warning_codes(response)
    assert response.status == "completed"


def test_same_input_produces_identical_output() -> None:
    data = {
        "campaign": {"status": "active", "campaign_type": "single_release"},
        "track": {"release_date": "2026-06-20"},
        "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
    }
    first = service.recommend(_request(data, REF)).model_dump()
    second = service.recommend(_request(data, REF)).model_dump()

    assert first == second


def test_envelope_explains_the_scoring_basis() -> None:
    response = _recommend({"campaign": {"status": "active"}}, REF)
    assert any(e.code == "scoring_basis" for e in response.explanations)


def test_metadata_echoes_payload_version_without_timestamp() -> None:
    response = _recommend({"campaign": {"status": "active"}}, REF)
    assert response.metadata.payload_version == "1.0"
    assert response.metadata.generated_at is None
