"""Scoring contracts (backlog section 7.3).

Every score is 0–100 or `null` (when not computable → reported as "unknown"
alongside a warning by the engine). Weights/rules are the engine's concern
(IE-005); this module only fixes the shape.
"""

from pydantic import BaseModel, Field

from app.schemas.campaign import CampaignRequest
from app.schemas.common import Grade, Score
from app.schemas.responses import IntelligenceResponse


class ScoreSet(BaseModel):
    campaign_readiness_score: Score | None = None
    momentum_score: Score | None = None
    content_opportunity_score: Score | None = None
    risk_score: Score | None = None
    priority_score: Score | None = None


class ScoringResult(BaseModel):
    scores: ScoreSet = Field(default_factory=ScoreSet)
    grade: Grade = "unknown"


class ScoringRequest(CampaignRequest):
    """Request body for POST /scoring/campaign."""


ScoringResponse = IntelligenceResponse[ScoringResult]
