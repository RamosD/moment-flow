"""POST /analysis/campaign — campaign analysis (IE-004).

Validates the request, then delegates to the deterministic, explainable
`CampaignAnalysisService`. No generative AI, no external calls, no persistence.
"""

from fastapi import APIRouter, Depends

from app.api._openapi import IMPLEMENTED_ERROR_RESPONSES
from app.core.security import require_internal_token
from app.schemas.campaign import CampaignAnalysisRequest, CampaignAnalysisResponse
from app.services.campaign_analysis import campaign_analysis_service

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
    dependencies=[Depends(require_internal_token)],
)


@router.post(
    "/campaign",
    response_model=CampaignAnalysisResponse,
    responses=IMPLEMENTED_ERROR_RESPONSES,
)
def analyse_campaign(payload: CampaignAnalysisRequest) -> CampaignAnalysisResponse:
    return campaign_analysis_service.analyse(payload)
