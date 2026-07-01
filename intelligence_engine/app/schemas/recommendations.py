"""Recommendation contracts (backlog section 7.4).

A recommendation only ever *suggests* an action plus an optional content pack
and expected outputs — it never creates Django entities and never calls the
renderer. `suggested_content_pack` and `output_type` are constrained to values
the Backend Core / renderer actually support (risk IE-RSK-005).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.campaign import CampaignRequest
from app.schemas.common import (
    ActionType,
    ConfidenceScore,
    ContentPackKey,
    Explanation,
    NonEmptyStr,
    OutputType,
    Priority,
)
from app.schemas.responses import IntelligenceResponse


class ExpectedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_type: OutputType
    format: str | None = None
    template_key: str | None = None


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ActionType
    priority: Priority
    confidence: ConfidenceScore
    reason: NonEmptyStr
    suggested_content_pack: ContentPackKey | None = None
    expected_outputs: list[ExpectedOutput] = Field(default_factory=list)
    # Per-recommendation, machine-traceable justification (the trigger signal).
    # The response envelope also carries consolidated `explanations`.
    explanations: list[Explanation] = Field(default_factory=list)


class RecommendationsResult(BaseModel):
    recommendations: list[Recommendation] = Field(default_factory=list)


class RecommendationsRequest(CampaignRequest):
    """Request body for POST /recommendations/campaign."""


RecommendationsResponse = IntelligenceResponse[RecommendationsResult]
