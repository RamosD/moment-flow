"""Composite intelligence contract (backlog section 8 / IE-008).

`POST /intelligence/campaign` aggregates analysis, scoring, moment detection
and recommendations into a single response so the Backend Core can obtain a
full diagnostic in one call. This module only fixes the aggregated shape; the
orchestration logic is IE-008.
"""

from pydantic import BaseModel, Field

from app.schemas.campaign import CampaignAnalysisResult, CampaignRequest
from app.schemas.common import Grade
from app.schemas.moments import Moment
from app.schemas.recommendations import Recommendation
from app.schemas.responses import IntelligenceResponse
from app.schemas.scoring import ScoreSet


class IntelligenceResult(BaseModel):
    analysis: CampaignAnalysisResult = Field(default_factory=CampaignAnalysisResult)
    scores: ScoreSet = Field(default_factory=ScoreSet)
    grade: Grade = "unknown"
    moments: list[Moment] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str = ""


class IntelligenceCampaignRequest(CampaignRequest):
    """Request body for POST /intelligence/campaign."""


IntelligenceCampaignResponse = IntelligenceResponse[IntelligenceResult]
