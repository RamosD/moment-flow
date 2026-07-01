"""POST /intelligence/campaign — composite diagnostic (IE-008).

Validates the request, then delegates to the deterministic
`IntelligenceOrchestrator`, which runs and aggregates the analysis, scoring,
moment-detection and recommendation engines. No Backend Core calls, no renderer
calls, no persistence.
"""

from fastapi import APIRouter, Depends

from app.api._openapi import IMPLEMENTED_ERROR_RESPONSES
from app.core.security import require_internal_token
from app.schemas.intelligence import IntelligenceCampaignRequest, IntelligenceCampaignResponse
from app.services.intelligence_orchestrator import intelligence_orchestrator

router = APIRouter(
    prefix="/intelligence",
    tags=["intelligence"],
    dependencies=[Depends(require_internal_token)],
)


@router.post(
    "/campaign",
    response_model=IntelligenceCampaignResponse,
    responses=IMPLEMENTED_ERROR_RESPONSES,
)
def analyse_campaign_composite(
    payload: IntelligenceCampaignRequest,
) -> IntelligenceCampaignResponse:
    return intelligence_orchestrator.run(payload)
