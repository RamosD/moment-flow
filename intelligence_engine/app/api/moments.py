"""POST /moments/detect — moment detection (IE-007).

Validates the request, then delegates to the deterministic, explainable
`MomentDetector`. No generative AI, no scraping, no external calls, no
persistence. Each detected moment recommends an action the recommendation
engine can fulfil.
"""

from fastapi import APIRouter, Depends

from app.api._openapi import IMPLEMENTED_ERROR_RESPONSES
from app.core.security import require_internal_token
from app.schemas.moments import MomentsRequest, MomentsResponse
from app.services.moment_detector import moment_detector

router = APIRouter(
    prefix="/moments",
    tags=["moments"],
    dependencies=[Depends(require_internal_token)],
)


@router.post(
    "/detect",
    response_model=MomentsResponse,
    responses=IMPLEMENTED_ERROR_RESPONSES,
)
def detect_moments(payload: MomentsRequest) -> MomentsResponse:
    return moment_detector.detect(payload)
