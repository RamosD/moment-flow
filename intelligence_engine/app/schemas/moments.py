"""Moment detection contracts (backlog section 7.5).

Each detected moment carries a type, severity, numeric confidence and a
summary, plus an optional `recommended_action` constrained to the same
vocabulary as the recommendation engine (so moments and recommendations stay
mutually consistent).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.campaign import CampaignRequest
from app.schemas.common import (
    ActionType,
    ConfidenceScore,
    Explanation,
    MomentType,
    NonEmptyStr,
    Severity,
)
from app.schemas.responses import IntelligenceResponse


class Moment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MomentType
    severity: Severity
    confidence: ConfidenceScore
    summary: NonEmptyStr
    recommended_action: ActionType | None = None
    # Per-moment, machine-traceable justification (the detected signal).
    explanations: list[Explanation] = Field(default_factory=list)


class MomentsResult(BaseModel):
    moments: list[Moment] = Field(default_factory=list)


class MomentsRequest(CampaignRequest):
    """Request body for POST /moments/detect."""


MomentsResponse = IntelligenceResponse[MomentsResult]
