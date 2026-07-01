"""POST /recommendations/campaign — campaign recommendations (IE-006).

Validates the request, then delegates to the deterministic, explainable
`RecommendationEngine`. The engine only *suggests* actions — it never creates
Django entities, never calls the renderer, and never persists anything.
"""

from fastapi import APIRouter, Depends

from app.api._openapi import IMPLEMENTED_ERROR_RESPONSES
from app.core.security import require_internal_token
from app.schemas.recommendations import RecommendationsRequest, RecommendationsResponse
from app.services.recommendation_engine import recommendation_engine

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    dependencies=[Depends(require_internal_token)],
)


@router.post(
    "/campaign",
    response_model=RecommendationsResponse,
    responses=IMPLEMENTED_ERROR_RESPONSES,
)
def recommend_campaign(payload: RecommendationsRequest) -> RecommendationsResponse:
    return recommendation_engine.recommend(payload)
