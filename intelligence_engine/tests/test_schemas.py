"""Schema-level validation tests (IE-003).

These exercise the Pydantic contracts directly (no HTTP), covering valid and
invalid payloads, the payload_version rule, the closed entity vocabulary, and
the numeric bounds on scores and confidence.
"""

import pytest
from pydantic import ValidationError

from app.schemas.campaign import CampaignAnalysisRequest, CampaignAnalysisResponse
from app.schemas.common import EntityRef
from app.schemas.moments import Moment
from app.schemas.recommendations import Recommendation
from app.schemas.scoring import ScoreSet, ScoringResponse

VALID_ENVELOPE = {
    "payload_version": "1.0",
    "workspace_id": "ws-1",
    "request_id": "req-1",
    "entity": {"type": "campaign", "id": "campaign-1"},
}


def test_minimal_valid_request_parses_with_empty_data_bundle() -> None:
    req = CampaignAnalysisRequest.model_validate(VALID_ENVELOPE)

    assert req.workspace_id == "ws-1"
    assert req.entity.type == "campaign"
    # data defaults to an empty bundle, not None.
    assert req.data.content_outputs == []


def test_request_accepts_rich_but_permissive_data_bundle() -> None:
    payload = {
        **VALID_ENVELOPE,
        "data": {
            "campaign": {"id": "c1", "status": "active", "unexpected_field": "kept"},
            "smart_link_stats": {"total_clicks": 1200, "clicks_last_7_days": 90},
            "content_outputs": [{"id": "o1", "output_type": "post", "status": "completed"}],
        },
    }

    req = CampaignAnalysisRequest.model_validate(payload)

    assert req.data.smart_link_stats.total_clicks == 1200
    # Permissive sub-models keep unknown fields rather than rejecting them.
    assert req.data.campaign.model_extra["unexpected_field"] == "kept"


@pytest.mark.parametrize(
    "mutation",
    [
        {"payload_version": "2.0"},
        {"payload_version": "0.9"},
        {"payload_version": ""},
        {"workspace_id": ""},
        {"request_id": "   "},
        {"entity": {"type": "planet", "id": "x"}},
        {"entity": {"type": "campaign"}},  # missing id
        {"entity": {"type": "campaign", "id": "c", "extra": "no"}},  # forbid extra
    ],
)
def test_invalid_envelopes_are_rejected(mutation: dict) -> None:
    payload = {**VALID_ENVELOPE, **mutation}
    with pytest.raises(ValidationError):
        CampaignAnalysisRequest.model_validate(payload)


def test_unknown_top_level_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CampaignAnalysisRequest.model_validate({**VALID_ENVELOPE, "surprise": 1})


def test_entity_ref_closed_vocabulary() -> None:
    known_types = ("campaign", "artist", "track", "content_pack_request", "report", "media_kit")
    for entity_type in known_types:
        assert EntityRef(type=entity_type, id="x").type == entity_type
    with pytest.raises(ValidationError):
        EntityRef(type="label", id="x")


def test_score_bounds_enforced() -> None:
    ScoreSet(campaign_readiness_score=0, risk_score=100)  # bounds ok
    assert ScoreSet().momentum_score is None  # unknown == None
    with pytest.raises(ValidationError):
        ScoreSet(momentum_score=101)
    with pytest.raises(ValidationError):
        ScoreSet(risk_score=-1)


def test_confidence_bounds_enforced() -> None:
    Recommendation(action="create_release_post", priority="high", confidence=0.82, reason="ok")
    with pytest.raises(ValidationError):
        Recommendation(action="no_action", priority="low", confidence=1.5, reason="x")


def test_recommendation_content_pack_is_constrained() -> None:
    rec = Recommendation(
        action="create_release_post",
        priority="high",
        confidence=0.8,
        reason="signals present",
        suggested_content_pack="release_pack",
        expected_outputs=[
            {"output_type": "post", "format": "post_1_1", "template_key": "release_card"}
        ],
    )
    assert rec.suggested_content_pack == "release_pack"
    with pytest.raises(ValidationError):
        Recommendation(
            action="create_release_post",
            priority="high",
            confidence=0.8,
            reason="x",
            suggested_content_pack="nonexistent_pack",
        )


def test_moment_requires_known_type_and_severity() -> None:
    Moment(type="milestone_reached", severity="medium", confidence=0.7, summary="ok")
    with pytest.raises(ValidationError):
        Moment(type="went_viral", severity="medium", confidence=0.7, summary="x")


def test_response_envelope_has_stable_defaults() -> None:
    resp = ScoringResponse(request_id="req-1", workspace_id="ws-1", result={})

    assert resp.status == "completed"
    assert resp.engine == "intelligence_engine"
    assert resp.engine_version == "0.1.0"
    assert resp.explanations == []
    assert resp.warnings == []
    # result coerced into a typed ScoringResult with its own defaults.
    assert resp.result.grade == "unknown"


def test_analysis_response_serialises_to_contract_shape() -> None:
    resp = CampaignAnalysisResponse(
        request_id="req-1",
        workspace_id="ws-1",
        result={"campaign_health": "good", "summary": "Healthy"},
        explanations=[{"code": "has_outputs", "message": "Recent content", "weight": 0.3}],
    )
    dumped = resp.model_dump()

    assert dumped["result"]["campaign_health"] == "good"
    assert dumped["explanations"][0]["weight"] == 0.3
    assert dumped["metadata"] == {"generated_at": None, "payload_version": None}
