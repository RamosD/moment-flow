"""POST /scoring/campaign — campaign scoring (IE-005).

Validates the request, then delegates to the deterministic, explainable
`ScoringEngine`. No generative AI, no external calls, no persistence.
"""

from fastapi import APIRouter, Depends

from app.api._openapi import IMPLEMENTED_ERROR_RESPONSES
from app.core.security import require_internal_token
from app.schemas.scoring import ScoringRequest, ScoringResponse
from app.services.scoring_engine import scoring_engine

router = APIRouter(
    prefix="/scoring",
    tags=["scoring"],
    dependencies=[Depends(require_internal_token)],
)


@router.post(
    "/campaign",
    response_model=ScoringResponse,
    responses=IMPLEMENTED_ERROR_RESPONSES,
)
def score_campaign(payload: ScoringRequest) -> ScoringResponse:
    return scoring_engine.score(payload)
