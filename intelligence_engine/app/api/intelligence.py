"""POST /intelligence/campaign — composite diagnostic (IE-008).

Validates the request, then delegates to the deterministic
`IntelligenceOrchestrator`, which runs and aggregates the analysis, scoring,
moment-detection and recommendation engines. No Backend Core calls, no renderer
calls, no persistence.
"""

from fastapi import APIRouter, Depends

from app.api._openapi import IMPLEMENTED_ERROR_RESPONSES
from app.core.logging import get_logger
from app.core.security import require_internal_token
from app.schemas.intelligence import IntelligenceCampaignRequest, IntelligenceCampaignResponse
from app.services.intelligence_orchestrator import intelligence_orchestrator

router = APIRouter(
    prefix="/intelligence",
    tags=["intelligence"],
    dependencies=[Depends(require_internal_token)],
)

logger = get_logger("intelligence_engine.intelligence")


@router.post(
    "/campaign",
    response_model=IntelligenceCampaignResponse,
    responses=IMPLEMENTED_ERROR_RESPONSES,
)
def analyse_campaign_composite(
    payload: IntelligenceCampaignRequest,
) -> IntelligenceCampaignResponse:
    # App-level correlation logging (STG-PRE-005 / OBS-L01): request_id comes
    # from the Backend Core (its request.correlation_id when the call
    # originated from an HTTP request); logging it here ties this service's
    # own logs back to the same operation. Never logs the payload itself
    # (campaign/track analytics data), only ids.
    logger.info(
        "intelligence.request_received",
        extra={"request_id": payload.request_id, "workspace_id": payload.workspace_id},
    )
    result = intelligence_orchestrator.run(payload)
    logger.info(
        "intelligence.request_completed",
        extra={"request_id": payload.request_id, "workspace_id": payload.workspace_id},
    )
    return result
