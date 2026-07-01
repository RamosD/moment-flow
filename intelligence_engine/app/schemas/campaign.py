"""Campaign analysis contracts and the shared campaign data bundle.

`CampaignDataBundle` is the opaque-ish payload Django sends to every
campaign-centric endpoint (analysis, scoring, recommendations, moments,
composite). Its sub-models name the fields the engine is expected to read
(per the MVP heuristics in the backlog) but stay permissive (`extra="allow"`)
so the Backend Core can enrich the payload without breaking the contract —
this is the loose-coupling lever called out in risk IE-RSK-008.

Field shapes mirror the Backend Core models (apps.campaigns, apps.catalogue,
apps.content, apps.reports, apps.links) without importing them.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseIntelligenceRequest, CampaignHealth
from app.schemas.responses import IntelligenceResponse

_Permissive = ConfigDict(extra="allow")


class CampaignInfo(BaseModel):
    model_config = _Permissive

    id: str | None = None
    name: str | None = None
    campaign_type: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    primary_goal: str | None = None


class ArtistInfo(BaseModel):
    model_config = _Permissive

    id: str | None = None
    name: str | None = None
    primary_genre: str | None = None
    status: str | None = None


class TrackInfo(BaseModel):
    model_config = _Permissive

    id: str | None = None
    title: str | None = None
    release_date: date | None = None
    track_type: str | None = None
    status: str | None = None


class SmartLinkStats(BaseModel):
    model_config = _Permissive

    total_clicks: int | None = None
    clicks_last_7_days: int | None = None
    clicks_last_30_days: int | None = None
    active_links: int | None = None


class ContentOutputSummary(BaseModel):
    model_config = _Permissive

    id: str | None = None
    output_type: str | None = None
    status: str | None = None
    created_at: date | None = None


class ReportSummary(BaseModel):
    model_config = _Permissive

    id: str | None = None
    report_type: str | None = None
    status: str | None = None
    period_end: date | None = None


class MediaKitSummary(BaseModel):
    model_config = _Permissive

    id: str | None = None
    status: str | None = None


class CampaignDataBundle(BaseModel):
    """The campaign-centric payload shared by all campaign endpoints."""

    model_config = _Permissive

    campaign: CampaignInfo | None = None
    artist: ArtistInfo | None = None
    track: TrackInfo | None = None
    smart_link_stats: SmartLinkStats | None = None
    content_outputs: list[ContentOutputSummary] = Field(default_factory=list)
    previous_reports: list[ReportSummary] = Field(default_factory=list)
    media_kits: list[MediaKitSummary] = Field(default_factory=list)
    goals: list[dict[str, Any]] = Field(default_factory=list)


class CampaignRequest(BaseIntelligenceRequest):
    """Base request for every campaign-centric endpoint.

    Each endpoint subclasses this for a distinct OpenAPI schema name while
    sharing the identical, validated shape. `data` defaults to an empty bundle
    so a minimal valid envelope (without analytics) still validates — the
    engines treat missing data as "unknown" rather than an error.
    """

    data: CampaignDataBundle = Field(default_factory=CampaignDataBundle)


# --- Campaign analysis contract (backlog section 7.2) -------------------------


class CampaignAnalysisRequest(CampaignRequest):
    """Request body for POST /analysis/campaign."""


class CampaignAnalysisResult(BaseModel):
    campaign_health: CampaignHealth = "unknown"
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


CampaignAnalysisResponse = IntelligenceResponse[CampaignAnalysisResult]
