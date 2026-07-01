"""GET /health — public liveness probe. No authentication required."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.core.config import Settings

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    settings: Settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }
