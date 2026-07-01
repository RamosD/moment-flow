"""Deterministic, explainable campaign analysis (IE-004).

No generative AI, no external calls, no persistence. The same input always
produces the same output.

Determinism and time
--------------------
Every time-based rule is anchored to an explicit `reference_date` taken from
the request `context` (`context["reference_date"]`, ISO `YYYY-MM-DD`). When it
is absent, recency rules degrade to *presence*-based ones rather than reading
the wall clock, so results never depend on when the service runs. A malformed
`reference_date` becomes a warning, never a 500.

Heuristic rules (all documented, all explainable)
-------------------------------------------------
- R0  empty data bundle                  -> health unknown + warning `insufficient_data`
- R1  completed content outputs present  -> strength `has_content_outputs`
- R1b ...and recent (window, if datable) -> strength `recent_content_outputs`
- R2  no completed content outputs       -> opportunity `content_gap`
- R3  smart link has positive activity   -> strength `smart_link_activity`
- R4  smart link present, all-zero       -> weakness `smart_link_no_activity`
- R4b smart link stats absent            -> warning `smart_link_stats_missing`
- R5  no recent completed report         -> opportunity `report_due`
- R6  no usable media kit                -> opportunity `media_kit_missing`
- R7  active campaign, no traction       -> risk `active_campaign_no_traction`
- C1  end_date < start_date              -> warning `inconsistent_campaign_dates`
- C2  negative smart-link counters       -> warning `negative_smart_link_stats`
- C3  content output after reference     -> warning `future_content_output_date`

Health is then derived from the collected signals:
  - `unknown`  — insufficient data (R0);
  - `critical` — at least one risk and no strengths;
  - `warning`  — any risk or weakness (but not critical), or signals present
                 without a clear positive lean;
  - `good`     — strengths present, no risks, no weaknesses.
"""

from datetime import date, timedelta

from app.schemas.campaign import (
    CampaignAnalysisRequest,
    CampaignAnalysisResponse,
    CampaignAnalysisResult,
    CampaignDataBundle,
    SmartLinkStats,
)
from app.schemas.common import CampaignHealth, Explanation, Warning
from app.schemas.responses import ResponseMetadata

# Tunable, documented thresholds (deterministic; no wall-clock dependency).
RECENT_CONTENT_WINDOW_DAYS = 14
REPORT_DUE_AFTER_DAYS = 30

_COMPLETED_OUTPUT_STATUSES = {"completed"}
_COMPLETED_REPORT_STATUSES = {"completed"}
_USABLE_MEDIA_KIT_STATUSES = {"generated", "published"}
_ACTIVE_CAMPAIGN_STATUS = "active"


class CampaignAnalysisService:
    """Stateless heuristic analyser. Safe to share as a singleton."""

    def analyse(self, request: CampaignAnalysisRequest) -> CampaignAnalysisResponse:
        data = request.data
        warnings: list[Warning] = []
        reference_date = self._parse_reference_date(request.context, warnings)

        if self._is_insufficient(data):
            warnings.append(
                Warning(
                    code="insufficient_data",
                    message="Not enough campaign data to produce an analysis.",
                )
            )
            result = CampaignAnalysisResult(
                campaign_health="unknown",
                summary="Insufficient data to analyse this campaign.",
            )
            return self._build(request, result, explanations=[], warnings=warnings)

        strengths: list[str] = []
        weaknesses: list[str] = []
        opportunities: list[str] = []
        risks: list[str] = []
        explanations: list[Explanation] = []

        self._check_consistency(data, reference_date, warnings)

        content_gap = self._eval_content_outputs(
            data, reference_date, strengths, opportunities, explanations
        )
        smart_link_active = self._eval_smart_links(
            data.smart_link_stats, strengths, weaknesses, explanations, warnings
        )
        self._eval_reports(data, reference_date, opportunities, explanations)
        self._eval_media_kit(data, opportunities, explanations)
        self._eval_risk(data, content_gap, smart_link_active, risks, explanations)

        health = self._derive_health(strengths, weaknesses, risks)
        result = CampaignAnalysisResult(
            campaign_health=health,
            summary=self._summary(health, strengths, weaknesses, opportunities, risks),
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            risks=risks,
        )
        return self._build(request, result, explanations, warnings)

    # --- individual rule groups ------------------------------------------------

    def _eval_content_outputs(
        self,
        data: CampaignDataBundle,
        reference_date: date | None,
        strengths: list[str],
        opportunities: list[str],
        explanations: list[Explanation],
    ) -> bool:
        """Returns True when there is a content gap (no completed outputs)."""
        completed = [
            output
            for output in data.content_outputs
            if (output.status or "").lower() in _COMPLETED_OUTPUT_STATUSES
        ]
        if not completed:
            opportunities.append("No content has been produced for this campaign yet.")
            explanations.append(
                Explanation(
                    code="content_gap",
                    message="The campaign has no completed content outputs.",
                    weight=0.3,
                )
            )
            return True

        strengths.append("The campaign has produced content outputs.")
        explanations.append(
            Explanation(
                code="has_content_outputs",
                message=f"{len(completed)} completed content output(s) found.",
                weight=0.2,
            )
        )

        if reference_date is not None:
            cutoff = reference_date - timedelta(days=RECENT_CONTENT_WINDOW_DAYS)
            recent = [
                output
                for output in completed
                if output.created_at and cutoff <= output.created_at <= reference_date
            ]
            if recent:
                strengths.append("Recent content output activity.")
                explanations.append(
                    Explanation(
                        code="recent_content_outputs",
                        message=(
                            f"{len(recent)} content output(s) produced within the last "
                            f"{RECENT_CONTENT_WINDOW_DAYS} days."
                        ),
                        weight=0.25,
                    )
                )
        return False

    def _eval_smart_links(
        self,
        stats: SmartLinkStats | None,
        strengths: list[str],
        weaknesses: list[str],
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> bool:
        """Returns True when smart links show positive activity."""
        if stats is None:
            warnings.append(
                Warning(
                    code="smart_link_stats_missing",
                    message="No smart-link statistics were provided; engagement was not assessed.",
                )
            )
            return False

        if self._smart_link_has_activity(stats):
            strengths.append("Smart links are receiving activity.")
            explanations.append(
                Explanation(
                    code="smart_link_activity",
                    message="Smart links show positive click/engagement activity.",
                    weight=0.2,
                )
            )
            return True

        weaknesses.append("Smart links show no activity.")
        explanations.append(
            Explanation(
                code="smart_link_no_activity",
                message="Smart-link statistics are present but show no clicks or active links.",
                weight=0.2,
            )
        )
        return False

    def _eval_reports(
        self,
        data: CampaignDataBundle,
        reference_date: date | None,
        opportunities: list[str],
        explanations: list[Explanation],
    ) -> None:
        if self._has_recent_completed_report(data, reference_date):
            return
        opportunities.append("No recent report is available for this campaign.")
        explanations.append(
            Explanation(
                code="report_due",
                message="There is no recent completed report; a report may be due.",
                weight=0.2,
            )
        )

    def _eval_media_kit(
        self,
        data: CampaignDataBundle,
        opportunities: list[str],
        explanations: list[Explanation],
    ) -> None:
        has_usable = any(
            (kit.status or "").lower() in _USABLE_MEDIA_KIT_STATUSES for kit in data.media_kits
        )
        if has_usable:
            return
        opportunities.append("No media kit is available for this campaign.")
        explanations.append(
            Explanation(
                code="media_kit_missing",
                message="The campaign has no generated or published media kit.",
                weight=0.15,
            )
        )

    def _eval_risk(
        self,
        data: CampaignDataBundle,
        content_gap: bool,
        smart_link_active: bool,
        risks: list[str],
        explanations: list[Explanation],
    ) -> None:
        status = (data.campaign.status or "").lower() if data.campaign else ""
        if status == _ACTIVE_CAMPAIGN_STATUS and content_gap and not smart_link_active:
            risks.append("Active campaign with no content and no smart-link traction.")
            explanations.append(
                Explanation(
                    code="active_campaign_no_traction",
                    message=(
                        "The campaign is active but has neither produced content nor gained "
                        "smart-link traction."
                    ),
                    weight=0.4,
                )
            )

    # --- consistency checks (never raise; only warn) ---------------------------

    def _check_consistency(
        self,
        data: CampaignDataBundle,
        reference_date: date | None,
        warnings: list[Warning],
    ) -> None:
        campaign = data.campaign
        if (
            campaign
            and campaign.start_date
            and campaign.end_date
            and campaign.end_date < campaign.start_date
        ):
            warnings.append(
                Warning(
                    code="inconsistent_campaign_dates",
                    message="Campaign end_date is before start_date.",
                )
            )

        stats = data.smart_link_stats
        if stats is not None and self._smart_link_has_negative(stats):
            warnings.append(
                Warning(
                    code="negative_smart_link_stats",
                    message="Smart-link statistics contain negative values; treated as inactive.",
                )
            )

        if reference_date is not None:
            future = [
                output
                for output in data.content_outputs
                if output.created_at and output.created_at > reference_date
            ]
            if future:
                warnings.append(
                    Warning(
                        code="future_content_output_date",
                        message=(
                            f"{len(future)} content output(s) are dated after the reference date; "
                            "excluded from recency analysis."
                        ),
                    )
                )

    # --- small deterministic helpers -------------------------------------------

    @staticmethod
    def _smart_link_has_activity(stats: SmartLinkStats) -> bool:
        values = [
            stats.total_clicks,
            stats.clicks_last_7_days,
            stats.clicks_last_30_days,
            stats.active_links,
        ]
        return any(value is not None and value > 0 for value in values)

    @staticmethod
    def _smart_link_has_negative(stats: SmartLinkStats) -> bool:
        values = [
            stats.total_clicks,
            stats.clicks_last_7_days,
            stats.clicks_last_30_days,
            stats.active_links,
        ]
        return any(value is not None and value < 0 for value in values)

    @staticmethod
    def _has_recent_completed_report(data: CampaignDataBundle, reference_date: date | None) -> bool:
        completed = [
            report
            for report in data.previous_reports
            if (report.status or "").lower() in _COMPLETED_REPORT_STATUSES
        ]
        if not completed:
            return False
        dated = [report.period_end for report in completed if report.period_end]
        if reference_date is None or not dated:
            # A completed report exists but recency cannot/need not be assessed:
            # treat its presence as sufficient (avoid a false "report due").
            return True
        return any(
            (reference_date - period_end).days <= REPORT_DUE_AFTER_DAYS for period_end in dated
        )

    @staticmethod
    def _is_insufficient(data: CampaignDataBundle) -> bool:
        return (
            data.campaign is None
            and data.artist is None
            and data.track is None
            and data.smart_link_stats is None
            and not data.content_outputs
            and not data.previous_reports
            and not data.media_kits
            and not data.goals
        )

    @staticmethod
    def _parse_reference_date(context: dict, warnings: list[Warning]) -> date | None:
        raw = context.get("reference_date")
        if raw is None:
            return None
        if isinstance(raw, date):
            return raw
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw)
            except ValueError:
                warnings.append(
                    Warning(
                        code="invalid_reference_date",
                        message="context.reference_date is not a valid ISO date; ignored.",
                    )
                )
                return None
        warnings.append(
            Warning(
                code="invalid_reference_date",
                message="context.reference_date has an unexpected type; ignored.",
            )
        )
        return None

    @staticmethod
    def _derive_health(
        strengths: list[str], weaknesses: list[str], risks: list[str]
    ) -> CampaignHealth:
        if risks and not strengths:
            return "critical"
        if risks or weaknesses:
            return "warning"
        if strengths:
            return "good"
        return "warning"

    @staticmethod
    def _summary(
        health: CampaignHealth,
        strengths: list[str],
        weaknesses: list[str],
        opportunities: list[str],
        risks: list[str],
    ) -> str:
        return (
            f"Campaign health assessed as '{health}'. Signals — strengths: {len(strengths)}, "
            f"weaknesses: {len(weaknesses)}, opportunities: {len(opportunities)}, "
            f"risks: {len(risks)}."
        )

    @staticmethod
    def _build(
        request: CampaignAnalysisRequest,
        result: CampaignAnalysisResult,
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> CampaignAnalysisResponse:
        # `generated_at` is intentionally left unset to preserve determinism;
        # timestamping is the Backend Core's concern.
        return CampaignAnalysisResponse(
            request_id=request.request_id,
            workspace_id=request.workspace_id,
            result=result,
            explanations=explanations,
            warnings=warnings,
            metadata=ResponseMetadata(payload_version=request.payload_version),
        )


# Module-level singleton (the service is stateless).
campaign_analysis_service = CampaignAnalysisService()
