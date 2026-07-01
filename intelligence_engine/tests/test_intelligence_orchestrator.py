"""Unit tests for IntelligenceOrchestrator (IE-008).

Drive the orchestrator directly (no HTTP) and assert it aggregates the four
engines, consolidates explanations/warnings, stays deterministic, and degrades
a failing stage into a warning rather than raising.
"""

import pytest

from app.schemas.intelligence import IntelligenceCampaignRequest
from app.schemas.scoring import ScoringRequest
from app.services import intelligence_orchestrator as orchestrator_module
from app.services.intelligence_orchestrator import IntelligenceOrchestrator
from app.services.scoring_engine import scoring_engine

service = IntelligenceOrchestrator()

REF = {"reference_date": "2026-06-24"}

GOOD_DATA = {
    "campaign": {
        "status": "active",
        "campaign_type": "single_release",
        "primary_goal": "grow",
        "start_date": "2026-06-01",
        "end_date": "2026-12-31",
    },
    "artist": {"name": "Nova"},
    "track": {"release_date": "2026-06-25"},
    "smart_link_stats": {
        "total_clicks": 1500,
        "clicks_last_7_days": 25,
        "clicks_last_30_days": 300,
        "active_links": 4,
    },
    "content_outputs": [{"status": "completed", "created_at": "2026-06-22"}],
    "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
    "media_kits": [{"status": "published"}],
}


def _request(data: dict | None = None, context: dict | None = None) -> IntelligenceCampaignRequest:
    return IntelligenceCampaignRequest(
        payload_version="1.0",
        workspace_id="ws-1",
        request_id="req-1",
        entity={"type": "campaign", "id": "campaign-1"},
        context=context or {},
        data=data or {},
    )


def _run(data: dict | None = None, context: dict | None = None):
    return service.run(_request(data, context))


def _warning_codes(response) -> set[str]:
    return {warning.code for warning in response.warnings}


def _explanation_codes(response) -> set[str]:
    return {explanation.code for explanation in response.explanations}


# --- aggregation ---------------------------------------------------------------


def test_aggregates_all_four_sections() -> None:
    response = _run(GOOD_DATA, REF)
    result = response.result

    # analysis
    assert result.analysis.campaign_health in {"good", "warning", "critical", "unknown"}
    # scoring + grade
    assert result.scores.campaign_readiness_score is not None
    assert result.grade in {"A", "B", "C", "D", "unknown"}
    # moments + recommendations
    assert isinstance(result.moments, list)
    assert isinstance(result.recommendations, list)
    assert result.moments  # a release-window campaign produces moments
    assert result.recommendations
    # summary
    assert result.summary
    assert "grade" in result.summary.lower()


def test_envelope_status_is_completed() -> None:
    response = _run(GOOD_DATA, REF)
    assert response.status == "completed"
    assert response.engine == "intelligence_engine"


# --- consistency with the standalone services (isolation preserved) -----------


def test_scores_match_the_standalone_scoring_engine() -> None:
    # The composite reuses the scoring engine; results must be identical.
    composite = _run(GOOD_DATA, REF).result.scores.model_dump()
    standalone = scoring_engine.score(
        ScoringRequest.model_validate(_request(GOOD_DATA, REF).model_dump())
    ).result.scores.model_dump()

    assert composite == standalone


# --- consolidation -------------------------------------------------------------


def test_explanations_are_consolidated_across_stages() -> None:
    codes = _explanation_codes(_run(GOOD_DATA, REF))

    # Analysis rule codes, scoring score codes and the recommendation basis all
    # appear in one consolidated list.
    assert "campaign_readiness_score" in codes  # from scoring
    assert "scoring_basis" in codes  # from recommendations
    assert any(c in codes for c in ("has_content_outputs", "content_gap"))  # from analysis


def test_warnings_are_deduplicated_by_code() -> None:
    # Empty bundle makes every stage emit `insufficient_data`; it must appear once.
    response = _run({})
    codes = [w.code for w in response.warnings]

    assert codes.count("insufficient_data") == 1


def test_insufficient_data_is_handled_without_error() -> None:
    response = _run({})
    result = response.result

    assert response.status == "completed"
    assert result.analysis.campaign_health == "unknown"
    assert result.scores.campaign_readiness_score is None
    assert result.grade == "unknown"
    assert result.moments == []
    # Recommendations degrade to a single wait_for_more_data.
    assert [r.action for r in result.recommendations] == ["wait_for_more_data"]
    assert "insufficient_data" in _warning_codes(response)
    assert result.summary


# --- resilience: a failing stage becomes a warning, not a 500 ------------------


def test_failing_stage_degrades_to_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_request):
        raise RuntimeError("scoring blew up")

    # Patch the singleton the orchestrator actually calls.
    monkeypatch.setattr(orchestrator_module.scoring_engine, "score", _boom)

    response = service.run(_request(GOOD_DATA, REF))

    # No exception propagates; the scoring section is defaulted and flagged.
    assert response.status == "completed"
    assert "scoring_unavailable" in _warning_codes(response)
    assert response.result.scores.campaign_readiness_score is None
    assert response.result.grade == "unknown"
    # Other sections still ran.
    assert response.result.moments
    assert response.result.analysis.campaign_health in {"good", "warning", "critical", "unknown"}


# --- determinism ---------------------------------------------------------------


def test_same_input_produces_identical_output() -> None:
    first = service.run(_request(GOOD_DATA, REF)).model_dump()
    second = service.run(_request(GOOD_DATA, REF)).model_dump()

    assert first == second


def test_metadata_echoes_payload_version_without_timestamp() -> None:
    response = _run(GOOD_DATA, REF)

    assert response.metadata.payload_version == "1.0"
    assert response.metadata.generated_at is None
