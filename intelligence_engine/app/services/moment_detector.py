"""Deterministic, explainable moment detection (IE-007).

No generative AI, no scraping, no external API calls, no persistence. A moment
is a *sensor reading* over the campaign data bundle: it answers "is there a
simple, named opportunity that justifies a campaign action right now?". Detection
is purely a function of the payload (plus the explicit `context.reference_date`),
so the same input always yields the same ordered list of moments.

Relationship to the other engines
---------------------------------
The detector reads the shared data bundle directly with its own small,
documented predicates — it does not call the scoring or recommendation engines
(low coupling). It stays *consistent* with them in two ways: it reuses the same
thresholds (release window, report recency, milestone/weekly click thresholds),
and every `recommended_action` is an `ActionType` the recommendation engine can
emit, so a detected moment always maps to a fulfilable recommendation.

The eight MVP moments (backlog section 7.5)
-------------------------------------------
- release_window      — track release date within ±14 days of the reference
- weekly_growth       — weekly-growth campaign, or ≥20 clicks in the last 7 days
- milestone_reached   — milestone goal achieved / milestone campaign / ≥1000 total clicks
- low_engagement      — smart-link stats present but no activity
- content_gap         — campaign has no completed content (or only stale content)
- report_due          — no recent report, with substance worth reporting on
- media_kit_missing   — campaign without a usable media kit
- smart_link_activity — smart links receiving activity (and weekly_growth did not fire)

Insufficient data (empty bundle) → an empty `moments` list plus an explicit
`insufficient_data` warning. Consistency issues (inconsistent dates, negative
counters, malformed reference date) warn but never raise.
"""

from datetime import date, timedelta

from app.schemas.campaign import CampaignDataBundle, SmartLinkStats
from app.schemas.common import ActionType, Explanation, MomentType, Severity, Warning
from app.schemas.moments import Moment, MomentsRequest, MomentsResponse, MomentsResult
from app.schemas.responses import ResponseMetadata

# --- Documented thresholds (shared with scoring/recommendations; no wall clock)

RELEASE_WINDOW_DAYS = 14
RELEASE_IMMINENT_DAYS = 3
RECENT_CONTENT_WINDOW_DAYS = 14
REPORT_DUE_AFTER_DAYS = 30
MILESTONE_CLICKS_THRESHOLD = 1000
WEEKLY_GROWTH_CLICKS_THRESHOLD = 20

# Each moment maps to exactly one recommendation-engine action, keeping moments
# and recommendations mutually consistent (same ActionType vocabulary).
RECOMMENDED_ACTION: dict[MomentType, ActionType] = {
    "release_window": "create_release_post",
    "weekly_growth": "create_weekly_growth_post",
    "milestone_reached": "create_milestone_post",
    "low_engagement": "improve_smart_link",
    "content_gap": "create_release_post",
    "report_due": "create_report",
    "media_kit_missing": "create_media_kit",
    "smart_link_activity": "create_story",
}

# Per-signal confidence (deterministic; documented, never random).
CONFIDENCE: dict[str, float] = {
    "release_window_imminent": 0.90,
    "release_window": 0.80,
    "weekly_growth_type": 0.75,
    "weekly_growth_signal": 0.65,
    "milestone_goal": 0.85,
    "milestone_type": 0.80,
    "milestone_clicks": 0.65,
    "low_engagement": 0.75,
    "content_gap": 0.80,
    "content_gap_stale": 0.60,
    "report_due": 0.70,
    "media_kit_missing": 0.70,
    "smart_link_activity": 0.70,
}

_SEVERITY_RANK: dict[Severity, int] = {"high": 0, "medium": 1, "low": 2}

_RELEASE_CAMPAIGN_TYPES = {"single_release", "music_video_release", "album_release"}
_FINISHED_CAMPAIGN_STATUSES = {"completed", "archived"}
_COMPLETED_OUTPUT_STATUSES = {"completed"}
_COMPLETED_REPORT_STATUSES = {"completed"}
_USABLE_MEDIA_KIT_STATUSES = {"generated", "published"}


class MomentDetector:
    """Stateless heuristic detector. Safe to share as a singleton."""

    def detect(self, request: MomentsRequest) -> MomentsResponse:
        data = request.data
        warnings: list[Warning] = []
        reference_date = self._parse_reference_date(request.context, warnings)
        self._check_consistency(data, warnings)

        if self._is_insufficient(data):
            warnings.append(
                Warning(
                    code="insufficient_data",
                    message="Not enough campaign data to detect any moment.",
                )
            )
            return self._build(request, MomentsResult(moments=[]), warnings)

        moments: list[Moment] = []
        self._maybe(moments, self._release_window(data, reference_date))
        weekly = self._weekly_growth(data)
        self._maybe(moments, weekly)
        self._maybe(moments, self._milestone_reached(data))
        self._maybe(moments, self._low_engagement(data))
        self._maybe(moments, self._content_gap(data, reference_date))
        self._maybe(moments, self._report_due(data, reference_date))
        self._maybe(moments, self._media_kit_missing(data))
        self._maybe(moments, self._smart_link_activity(data, weekly_fired=weekly is not None))

        return self._build(request, MomentsResult(moments=self._sorted(moments)), warnings)

    # --- individual detections (each returns Moment | None) --------------------

    def _release_window(self, data: CampaignDataBundle, ref: date | None) -> Moment | None:
        track = data.track
        if track is None or track.release_date is None or ref is None:
            return None
        if self._status(data) in _FINISHED_CAMPAIGN_STATUSES:
            return None
        delta = abs((track.release_date - ref).days)
        if delta > RELEASE_WINDOW_DAYS:
            return None
        imminent = delta <= RELEASE_IMMINENT_DAYS
        return self._moment(
            "release_window",
            "high" if imminent else "medium",
            "release_window_imminent" if imminent else "release_window",
            f"The track release date is within {delta} day(s) of the reference date.",
            "release_window_detected",
            (
                f"Track release_date is {delta} day(s) from the reference date "
                f"(window {RELEASE_WINDOW_DAYS}d)."
            ),
        )

    def _weekly_growth(self, data: CampaignDataBundle) -> Moment | None:
        clicks_7d = self._clicks_7d(data.smart_link_stats)
        is_type = self._campaign_type(data) == "weekly_growth_campaign"
        if not (is_type or clicks_7d >= WEEKLY_GROWTH_CLICKS_THRESHOLD):
            return None
        if is_type:
            confidence_key = "weekly_growth_type"
            detail = "Campaign type is weekly_growth_campaign."
        else:
            confidence_key = "weekly_growth_signal"
            detail = (
                f"Smart-link clicks in the last 7 days ({clicks_7d}) cleared the weekly growth "
                f"threshold ({WEEKLY_GROWTH_CLICKS_THRESHOLD})."
            )
        return self._moment(
            "weekly_growth",
            "medium",
            confidence_key,
            "The campaign shows weekly growth worth highlighting.",
            "weekly_growth_detected",
            detail,
        )

    def _milestone_reached(self, data: CampaignDataBundle) -> Moment | None:
        if self._status(data) in _FINISHED_CAMPAIGN_STATUSES:
            return None
        achieved_goal = any(
            isinstance(goal, dict)
            and goal.get("goal_type") == "milestone"
            and goal.get("status") == "achieved"
            for goal in data.goals
        )
        clicks = self._total_clicks(data.smart_link_stats)
        if achieved_goal:
            severity: Severity = "high"
            confidence_key = "milestone_goal"
            detail = "A milestone goal has been achieved."
        elif self._campaign_type(data) == "milestone_campaign":
            severity = "high"
            confidence_key = "milestone_type"
            detail = "Campaign type is milestone_campaign."
        elif clicks >= MILESTONE_CLICKS_THRESHOLD:
            severity = "medium"
            confidence_key = "milestone_clicks"
            detail = (
                f"Smart-link total clicks ({clicks}) crossed the milestone threshold "
                f"({MILESTONE_CLICKS_THRESHOLD})."
            )
        else:
            return None
        return self._moment(
            "milestone_reached",
            severity,
            confidence_key,
            "The campaign reached a milestone worth celebrating.",
            "milestone_detected",
            detail,
        )

    def _low_engagement(self, data: CampaignDataBundle) -> Moment | None:
        stats = data.smart_link_stats
        if stats is None or self._smart_link_has_activity(stats):
            return None
        active = self._status(data) == "active"
        return self._moment(
            "low_engagement",
            "high" if active else "medium",
            "low_engagement",
            "Smart links are configured but show no engagement.",
            "low_engagement_detected",
            "Smart-link statistics are present but show no clicks or active links.",
        )

    def _content_gap(self, data: CampaignDataBundle, ref: date | None) -> Moment | None:
        if data.campaign is None:
            return None
        completed = self._completed_outputs(data)
        if not completed:
            active = self._status(data) == "active"
            return self._moment(
                "content_gap",
                "high" if active else "medium",
                "content_gap",
                "No completed content outputs exist for the campaign.",
                "content_gap_detected",
                "The campaign has no completed content outputs.",
            )
        if ref is not None and not self._has_recent_output(completed, ref):
            return self._moment(
                "content_gap",
                "low",
                "content_gap_stale",
                "The campaign's content is stale (nothing within the recent window).",
                "content_gap_stale_detected",
                (
                    f"No completed content output within the last {RECENT_CONTENT_WINDOW_DAYS} "
                    "days of the reference date."
                ),
            )
        return None

    def _report_due(self, data: CampaignDataBundle, ref: date | None) -> Moment | None:
        if data.campaign is None:
            return None
        status = self._status(data)
        if status not in {"active", "completed", "paused"}:
            return None
        if self._has_recent_completed_report(data, ref):
            return None
        has_substance = (
            bool(self._completed_outputs(data))
            or self._smart_link_has_activity(data.smart_link_stats)
            or status == "completed"
        )
        if not has_substance:
            return None
        return self._moment(
            "report_due",
            "medium",
            "report_due",
            "No recent report is available for the campaign.",
            "report_due_detected",
            "There is no recent completed report for the campaign.",
        )

    def _media_kit_missing(self, data: CampaignDataBundle) -> Moment | None:
        if data.campaign is None or self._has_usable_media_kit(data):
            return None
        status = self._status(data)
        is_media_campaign = self._campaign_type(data) == "media_campaign"
        if status == "draft" and not is_media_campaign:
            return None
        return self._moment(
            "media_kit_missing",
            "high" if is_media_campaign else "medium",
            "media_kit_missing",
            "The campaign has no usable media kit.",
            "media_kit_missing_detected",
            "No generated or published media kit exists for the campaign.",
        )

    def _smart_link_activity(
        self, data: CampaignDataBundle, *, weekly_fired: bool
    ) -> Moment | None:
        # Suppressed when weekly_growth fired (it already captures strong activity).
        if weekly_fired:
            return None
        stats = data.smart_link_stats
        if stats is None or not self._smart_link_has_activity(stats):
            return None
        return self._moment(
            "smart_link_activity",
            "low",
            "smart_link_activity",
            "Smart links are receiving active engagement.",
            "smart_link_activity_detected",
            "Smart-link statistics show positive click or active-link activity.",
        )

    # --- builders and helpers --------------------------------------------------

    @staticmethod
    def _moment(
        moment_type: MomentType,
        severity: Severity,
        confidence_key: str,
        summary: str,
        explanation_code: str,
        explanation_message: str,
    ) -> Moment:
        return Moment(
            type=moment_type,
            severity=severity,
            confidence=CONFIDENCE[confidence_key],
            summary=summary,
            recommended_action=RECOMMENDED_ACTION[moment_type],
            explanations=[Explanation(code=explanation_code, message=explanation_message)],
        )

    @staticmethod
    def _maybe(bucket: list[Moment], moment: Moment | None) -> None:
        if moment is not None:
            bucket.append(moment)

    @staticmethod
    def _sorted(moments: list[Moment]) -> list[Moment]:
        # Stable, deterministic ordering: severity, then confidence (desc), then
        # moment type (so ties never depend on detection order).
        return sorted(
            moments,
            key=lambda m: (_SEVERITY_RANK[m.severity], -m.confidence, m.type),
        )

    # --- consistency checks (never raise; only warn) ---------------------------

    def _check_consistency(self, data: CampaignDataBundle, warnings: list[Warning]) -> None:
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

    # --- small deterministic predicates ----------------------------------------

    @staticmethod
    def _status(data: CampaignDataBundle) -> str:
        return (data.campaign.status or "").lower() if data.campaign else ""

    @staticmethod
    def _campaign_type(data: CampaignDataBundle) -> str:
        return (data.campaign.campaign_type or "").lower() if data.campaign else ""

    @staticmethod
    def _total_clicks(stats: SmartLinkStats | None) -> int:
        return max(stats.total_clicks or 0, 0) if stats else 0

    @staticmethod
    def _clicks_7d(stats: SmartLinkStats | None) -> int:
        return max(stats.clicks_last_7_days or 0, 0) if stats else 0

    @staticmethod
    def _smart_link_has_activity(stats: SmartLinkStats | None) -> bool:
        if stats is None:
            return False
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
    def _completed_outputs(data: CampaignDataBundle) -> list:
        return [
            output
            for output in data.content_outputs
            if (output.status or "").lower() in _COMPLETED_OUTPUT_STATUSES
        ]

    @staticmethod
    def _has_recent_output(completed: list, ref: date) -> bool:
        cutoff = ref - timedelta(days=RECENT_CONTENT_WINDOW_DAYS)
        return any(output.created_at and cutoff <= output.created_at <= ref for output in completed)

    @staticmethod
    def _has_usable_media_kit(data: CampaignDataBundle) -> bool:
        return any(
            (kit.status or "").lower() in _USABLE_MEDIA_KIT_STATUSES for kit in data.media_kits
        )

    @staticmethod
    def _has_recent_completed_report(data: CampaignDataBundle, ref: date | None) -> bool:
        completed = [
            report
            for report in data.previous_reports
            if (report.status or "").lower() in _COMPLETED_REPORT_STATUSES
        ]
        if not completed:
            return False
        dated = [report.period_end for report in completed if report.period_end]
        if ref is None or not dated:
            return True
        return any((ref - period_end).days <= REPORT_DUE_AFTER_DAYS for period_end in dated)

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
    def _build(
        request: MomentsRequest,
        result: MomentsResult,
        warnings: list[Warning],
    ) -> MomentsResponse:
        # `generated_at` is intentionally left unset to preserve determinism;
        # timestamping is the Backend Core's concern. Each moment carries its own
        # explanations, so the envelope-level list stays empty.
        return MomentsResponse(
            request_id=request.request_id,
            workspace_id=request.workspace_id,
            result=result,
            explanations=[],
            warnings=warnings,
            metadata=ResponseMetadata(payload_version=request.payload_version),
        )


# Module-level singleton (the detector is stateless).
moment_detector = MomentDetector()
