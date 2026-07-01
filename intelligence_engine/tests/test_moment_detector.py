"""Unit tests for MomentDetector (IE-007).

One focused test per MVP moment type, plus the insufficient-data, determinism,
consistency and action-compatibility guarantees. Each test drives the detector
directly (no HTTP); the detector never touches Django, the renderer, or the
network.
"""

from typing import get_args

from app.schemas.common import ActionType
from app.schemas.moments import Moment, MomentsRequest
from app.services.moment_detector import CONFIDENCE, RECOMMENDED_ACTION, MomentDetector

service = MomentDetector()

REF = {"reference_date": "2026-06-24"}
_ACTION_VALUES = set(get_args(ActionType))


def _request(data: dict | None = None, context: dict | None = None) -> MomentsRequest:
    return MomentsRequest(
        payload_version="1.0",
        workspace_id="ws-1",
        request_id="req-1",
        entity={"type": "campaign", "id": "campaign-1"},
        context=context or {},
        data=data or {},
    )


def _detect(data: dict | None = None, context: dict | None = None):
    return service.detect(_request(data, context))


def _types(response) -> list[str]:
    return [moment.type for moment in response.result.moments]


def _by_type(response, moment_type: str) -> Moment | None:
    return next((m for m in response.result.moments if m.type == moment_type), None)


def _warning_codes(response) -> set[str]:
    return {warning.code for warning in response.warnings}


# --- release_window ------------------------------------------------------------


def test_release_window_imminent_is_high() -> None:
    response = _detect(
        {"campaign": {"status": "active"}, "track": {"release_date": "2026-06-25"}}, REF
    )
    moment = _by_type(response, "release_window")

    assert moment is not None
    assert moment.severity == "high"
    assert moment.recommended_action == "create_release_post"
    assert any(e.code == "release_window_detected" for e in moment.explanations)


def test_release_window_far_is_medium() -> None:
    response = _detect(
        {"campaign": {"status": "active"}, "track": {"release_date": "2026-07-05"}}, REF
    )
    moment = _by_type(response, "release_window")

    assert moment is not None
    assert moment.severity == "medium"


def test_no_release_window_outside_range() -> None:
    response = _detect(
        {"campaign": {"status": "active"}, "track": {"release_date": "2026-09-01"}}, REF
    )
    assert "release_window" not in _types(response)


# --- weekly_growth -------------------------------------------------------------


def test_weekly_growth_campaign_type_detected() -> None:
    response = _detect(
        {
            "campaign": {"status": "active", "campaign_type": "weekly_growth_campaign"},
            "smart_link_stats": {"clicks_last_7_days": 50},
        },
        REF,
    )
    moment = _by_type(response, "weekly_growth")

    assert moment is not None
    assert moment.severity == "medium"
    assert moment.recommended_action == "create_weekly_growth_post"
    # weekly_growth suppresses the standalone smart_link_activity moment.
    assert "smart_link_activity" not in _types(response)


def test_weekly_growth_click_signal_detected() -> None:
    response = _detect(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "smart_link_stats": {"clicks_last_7_days": 25},
        },
        REF,
    )
    moment = _by_type(response, "weekly_growth")

    assert moment is not None
    assert moment.confidence == CONFIDENCE["weekly_growth_signal"]


# --- milestone_reached ---------------------------------------------------------


def test_milestone_goal_achieved_is_high() -> None:
    response = _detect(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "goals": [{"goal_type": "milestone", "status": "achieved"}],
        },
        REF,
    )
    moment = _by_type(response, "milestone_reached")

    assert moment is not None
    assert moment.severity == "high"
    assert moment.recommended_action == "create_milestone_post"


def test_milestone_click_threshold_is_medium() -> None:
    response = _detect(
        {
            "campaign": {"status": "active"},
            "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 5},
        },
        REF,
    )
    moment = _by_type(response, "milestone_reached")

    assert moment is not None
    assert moment.severity == "medium"
    assert moment.confidence == CONFIDENCE["milestone_clicks"]


# --- low_engagement ------------------------------------------------------------


def test_low_engagement_for_inactive_smart_links() -> None:
    response = _detect(
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
    moment = _by_type(response, "low_engagement")

    assert moment is not None
    assert moment.severity == "high"
    assert moment.recommended_action == "improve_smart_link"
    # No activity → no smart_link_activity moment.
    assert "smart_link_activity" not in _types(response)


# --- content_gap ---------------------------------------------------------------


def test_content_gap_when_no_completed_content() -> None:
    response = _detect({"campaign": {"status": "draft"}}, REF)
    moment = _by_type(response, "content_gap")

    assert moment is not None
    assert moment.severity == "medium"  # draft, not active
    assert moment.recommended_action == "create_release_post"


def test_content_gap_stale_is_low() -> None:
    response = _detect(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-01-01"}],
        },
        REF,
    )
    moment = _by_type(response, "content_gap")

    assert moment is not None
    assert moment.severity == "low"


def test_recent_content_clears_content_gap() -> None:
    response = _detect(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-06-22"}],
        },
        REF,
    )
    assert "content_gap" not in _types(response)


# --- report_due ----------------------------------------------------------------


def test_report_due_when_no_recent_report() -> None:
    response = _detect(
        {
            "campaign": {"status": "completed"},
            "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
        },
        REF,
    )
    moment = _by_type(response, "report_due")

    assert moment is not None
    assert moment.recommended_action == "create_report"


def test_recent_report_clears_report_due() -> None:
    response = _detect(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
            "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
        },
        REF,
    )
    assert "report_due" not in _types(response)


# --- media_kit_missing ---------------------------------------------------------


def test_media_kit_missing_for_media_campaign_is_high() -> None:
    response = _detect({"campaign": {"status": "active", "campaign_type": "media_campaign"}}, REF)
    moment = _by_type(response, "media_kit_missing")

    assert moment is not None
    assert moment.severity == "high"
    assert moment.recommended_action == "create_media_kit"


def test_usable_media_kit_clears_moment() -> None:
    response = _detect(
        {"campaign": {"status": "active"}, "media_kits": [{"status": "published"}]}, REF
    )
    assert "media_kit_missing" not in _types(response)


# --- smart_link_activity -------------------------------------------------------


def test_smart_link_activity_detected() -> None:
    response = _detect(
        {
            "campaign": {"status": "active", "campaign_type": "custom"},
            "smart_link_stats": {"total_clicks": 50, "clicks_last_7_days": 5, "active_links": 2},
        },
        REF,
    )
    moment = _by_type(response, "smart_link_activity")

    assert moment is not None
    assert moment.severity == "low"
    assert moment.recommended_action == "create_story"


# --- insufficient data ---------------------------------------------------------


def test_insufficient_data_returns_empty_with_warning() -> None:
    response = _detect({})

    assert response.result.moments == []
    assert "insufficient_data" in _warning_codes(response)
    assert response.status == "completed"


# --- cross-cutting guarantees --------------------------------------------------


def test_every_moment_has_the_required_fields() -> None:
    response = _detect(
        {
            "campaign": {"status": "active", "campaign_type": "milestone_campaign"},
            "track": {"release_date": "2026-06-25"},
            "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
        },
        REF,
    )
    assert response.result.moments
    for moment in response.result.moments:
        assert moment.type
        assert moment.severity in {"low", "medium", "high"}
        assert 0.0 <= moment.confidence <= 1.0
        assert moment.summary
        assert moment.recommended_action is not None
        assert moment.explanations


def test_recommended_actions_are_recommendation_engine_compatible() -> None:
    # Static guarantee: every mapped action is part of the shared ActionType
    # vocabulary the recommendation engine emits.
    for action in RECOMMENDED_ACTION.values():
        assert action in _ACTION_VALUES

    # And every actually-emitted moment respects it.
    response = _detect(
        {
            "campaign": {"status": "active", "campaign_type": "media_campaign"},
            "track": {"release_date": "2026-06-25"},
            "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
        },
        REF,
    )
    for moment in response.result.moments:
        assert moment.recommended_action in _ACTION_VALUES


def test_moments_are_sorted_by_severity() -> None:
    response = _detect(
        {
            "campaign": {"status": "active"},
            "track": {"release_date": "2026-06-25"},
            "smart_link_stats": {
                "total_clicks": 0,
                "clicks_last_7_days": 0,
                "active_links": 0,
            },
        },
        REF,
    )
    ranks = [{"high": 0, "medium": 1, "low": 2}[m.severity] for m in response.result.moments]
    assert ranks == sorted(ranks)


def test_negative_smart_link_stats_warn_without_raising() -> None:
    response = _detect(
        {"campaign": {"status": "active"}, "smart_link_stats": {"total_clicks": -5}}, REF
    )
    assert "negative_smart_link_stats" in _warning_codes(response)
    assert response.status == "completed"


def test_invalid_reference_date_warns_and_does_not_raise() -> None:
    response = _detect({"campaign": {"status": "active"}}, {"reference_date": "not-a-date"})

    assert "invalid_reference_date" in _warning_codes(response)
    assert response.status == "completed"


def test_same_input_produces_identical_output() -> None:
    data = {
        "campaign": {"status": "active", "campaign_type": "single_release"},
        "track": {"release_date": "2026-06-25"},
        "smart_link_stats": {"total_clicks": 1500, "clicks_last_7_days": 25},
    }
    first = service.detect(_request(data, REF)).model_dump()
    second = service.detect(_request(data, REF)).model_dump()

    assert first == second


def test_metadata_echoes_payload_version_without_timestamp() -> None:
    response = _detect({"campaign": {"status": "active"}}, REF)

    assert response.metadata.payload_version == "1.0"
    assert response.metadata.generated_at is None
