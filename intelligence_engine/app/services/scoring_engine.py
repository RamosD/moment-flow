"""Deterministic, explainable campaign scoring (IE-005).

No generative AI, no external calls, no persistence. The same input always
produces the same output. Every score is justified: each computable score
carries one `Explanation` whose message enumerates the weighted components that
produced it; each non-computable score carries one `Warning` and a `null`
value. Nothing here is opaque — the numbers are a transparent weighted sum.

Determinism and time
--------------------
Like the analysis service, every time-based rule is anchored to an explicit
`reference_date` taken from `context["reference_date"]` (ISO `YYYY-MM-DD`).
When it is absent, recency rules degrade to *presence*-based ones rather than
reading the wall clock, so results never depend on when the service runs. A
malformed `reference_date` becomes a warning, never a 500.

The five scores (all 0–100, or `null`/"unknown" when not computable)
--------------------------------------------------------------------
Each score is `round(100 * Σ weightᵢ · valueᵢ)`, where every `valueᵢ ∈ [0,1]`
and the weights for that score sum to 1.0. A score is `null` only when its
required inputs are absent (see each `computable iff` note); a present-but-poor
campaign scores low rather than `null`.

1. campaign_readiness_score — how completely the campaign is set up to run.
   computable iff a `campaign` object is present.
     status_known    0.20  campaign.status is a known lifecycle status
     artist_present  0.15  artist data present
     track_present   0.15  track data present
     goal_defined    0.15  primary_goal set or goals listed
     schedule_defined 0.15 start_date present
     media_kit_ready 0.20  a usable (generated/published) media kit exists

2. momentum_score — current traction. Click-dominated by design: smart-link
   traction is the primary momentum signal.
   computable iff smart_link_stats present OR any content_outputs present.
     clicks_7d       0.40  saturate(clicks_last_7_days, 100)
     clicks_30d      0.25  saturate(clicks_last_30_days, 400)
     total_clicks    0.15  saturate(total_clicks, 2000)
     recent_content  0.20  saturate(recent completed outputs, 2)

3. content_opportunity_score — how much room there is to create content now.
   Higher = more unmet content need, weighted by timing relevance.
   computable iff any of campaign/track/content_outputs/previous_reports/
   media_kits is present.
     content_gap      0.35  no completed content (1.0) … recent content (0.0)
     report_due       0.20  no recent completed report
     media_kit_missing 0.20 no usable media kit
     timing_relevance 0.25  release window / active / scheduled / paused

4. risk_score — risk that the campaign under-performs. Higher = more risk.
   computable iff campaign present OR smart_link_stats present.
     no_traction       0.35  active + no content + no link activity
     link_inactivity   0.20  stats present but no clicks (0.5 if links, no clicks)
     content_gap_active 0.15 active campaign with no completed content
     overdue           0.15  end_date < reference_date and not completed/archived
     data_quality      0.15  inconsistent dates or negative smart-link counters

5. priority_score — how urgently to act on this campaign. A blend of the other
   four; risk *raises* priority (it needs attention). Weights are renormalised
   over whichever component scores are available.
     content_opportunity 0.35   momentum 0.25   risk 0.20   readiness 0.20
   computable iff at least two of those four are available.

Grade (A/B/C/D/unknown)
-----------------------
Derived from a separate `overall_standing` composite that reflects how well the
campaign is doing (not how urgently to act): a blend of readiness, momentum and
*inverted* risk (100 − risk), renormalised over whatever is available.
  A ≥ 80 · B ≥ 65 · C ≥ 45 · D < 45 · unknown when none of the three is available.

Consistency checks warn, never raise: inconsistent campaign dates, negative
smart-link counters, and content dated after the reference date.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.schemas.campaign import CampaignDataBundle, SmartLinkStats
from app.schemas.common import Explanation, Grade, Warning
from app.schemas.responses import ResponseMetadata
from app.schemas.scoring import ScoreSet, ScoringRequest, ScoringResponse, ScoringResult

# --- Documented thresholds (deterministic; no wall-clock dependency) ----------

RECENT_CONTENT_WINDOW_DAYS = 14
REPORT_DUE_AFTER_DAYS = 30
RELEASE_WINDOW_DAYS = 14

# Saturation points: a component reaches its full value (1.0) at/above these.
MOMENTUM_CLICKS_7D_SATURATION = 100
MOMENTUM_CLICKS_30D_SATURATION = 400
MOMENTUM_TOTAL_CLICKS_SATURATION = 2000
MOMENTUM_RECENT_OUTPUTS_SATURATION = 2

# Priority blend weights (also used as each score's Explanation.weight, so the
# explanation's `weight` field documents that score's share of priority).
PRIORITY_WEIGHTS: dict[str, float] = {
    "content_opportunity_score": 0.35,
    "momentum_score": 0.25,
    "risk_score": 0.20,
    "campaign_readiness_score": 0.20,
}

# Overall-standing blend weights (drives the grade). risk enters inverted.
STANDING_WEIGHTS: dict[str, float] = {
    "readiness": 0.35,
    "momentum": 0.35,
    "risk_inverted": 0.30,
}

GRADE_THRESHOLDS: tuple[tuple[int, Grade], ...] = (
    (80, "A"),
    (65, "B"),
    (45, "C"),
    (0, "D"),
)

_KNOWN_CAMPAIGN_STATUSES = {
    "draft",
    "scheduled",
    "active",
    "paused",
    "completed",
    "archived",
}
_COMPLETED_OUTPUT_STATUSES = {"completed"}
_COMPLETED_REPORT_STATUSES = {"completed"}
_USABLE_MEDIA_KIT_STATUSES = {"generated", "published"}
_ACTIVE_CAMPAIGN_STATUS = "active"
_FINISHED_CAMPAIGN_STATUSES = {"completed", "archived"}


@dataclass(frozen=True)
class Component:
    """One weighted contribution to a score. `value` is in [0, 1]."""

    key: str
    weight: float
    value: float


class ScoringEngine:
    """Stateless heuristic scorer. Safe to share as a singleton."""

    def score(self, request: ScoringRequest) -> ScoringResponse:
        data = request.data
        warnings: list[Warning] = []
        explanations: list[Explanation] = []

        reference_date = self._parse_reference_date(request.context, warnings)
        self._check_consistency(data, reference_date, warnings)

        readiness = self._collect(self._readiness(data), explanations, warnings)
        momentum = self._collect(self._momentum(data, reference_date), explanations, warnings)
        opportunity = self._collect(
            self._content_opportunity(data, reference_date), explanations, warnings
        )
        risk = self._collect(self._risk(data, reference_date), explanations, warnings)

        priority = self._collect(
            self._priority(readiness, momentum, opportunity, risk), explanations, warnings
        )

        grade = self._grade(readiness, momentum, risk, explanations, warnings)

        scores = ScoreSet(
            campaign_readiness_score=readiness,
            momentum_score=momentum,
            content_opportunity_score=opportunity,
            risk_score=risk,
            priority_score=priority,
        )

        if all(value is None for value in (readiness, momentum, opportunity, risk, priority)):
            warnings.append(
                Warning(
                    code="insufficient_data",
                    message="Not enough campaign data to compute any score.",
                )
            )

        result = ScoringResult(scores=scores, grade=grade)
        return self._build(request, result, explanations, warnings)

    # --- individual scores -----------------------------------------------------
    # Each returns (value | None, explanation | None, warning | None): either a
    # value with an explanation, or None with a warning. Never both, never
    # neither — so every score is always justified.

    def _readiness(
        self, data: CampaignDataBundle
    ) -> tuple[int | None, Explanation | None, Warning | None]:
        campaign = data.campaign
        if campaign is None:
            return None, None, self._unknown("campaign_readiness_score", "no campaign data")

        status_known = 1.0 if (campaign.status or "").lower() in _KNOWN_CAMPAIGN_STATUSES else 0.0
        goal_defined = 1.0 if ((campaign.primary_goal or "").strip() or data.goals) else 0.0
        components = [
            Component("status_known", 0.20, status_known),
            Component("artist_present", 0.15, 1.0 if data.artist is not None else 0.0),
            Component("track_present", 0.15, 1.0 if data.track is not None else 0.0),
            Component("goal_defined", 0.15, goal_defined),
            Component("schedule_defined", 0.15, 1.0 if campaign.start_date else 0.0),
            Component("media_kit_ready", 0.20, 1.0 if self._has_usable_media_kit(data) else 0.0),
        ]
        return self._scored("campaign_readiness_score", components)

    def _momentum(
        self, data: CampaignDataBundle, reference_date: date | None
    ) -> tuple[int | None, Explanation | None, Warning | None]:
        if data.smart_link_stats is None and not data.content_outputs:
            return (
                None,
                None,
                self._unknown("momentum_score", "no smart-link statistics or content outputs"),
            )

        clicks = self._clamped_clicks(data.smart_link_stats)
        components = [
            Component("clicks_7d", 0.40, _saturate(clicks["7d"], MOMENTUM_CLICKS_7D_SATURATION)),
            Component("clicks_30d", 0.25, _saturate(clicks["30d"], MOMENTUM_CLICKS_30D_SATURATION)),
            Component(
                "total_clicks", 0.15, _saturate(clicks["total"], MOMENTUM_TOTAL_CLICKS_SATURATION)
            ),
            Component("recent_content", 0.20, self._recent_content_value(data, reference_date)),
        ]
        return self._scored("momentum_score", components)

    def _content_opportunity(
        self, data: CampaignDataBundle, reference_date: date | None
    ) -> tuple[int | None, Explanation | None, Warning | None]:
        computable = (
            data.campaign is not None
            or data.track is not None
            or bool(data.content_outputs)
            or bool(data.previous_reports)
            or bool(data.media_kits)
        )
        if not computable:
            return (
                None,
                None,
                self._unknown(
                    "content_opportunity_score", "no campaign, content, report or media-kit data"
                ),
            )

        report_due = 0.0 if self._has_recent_completed_report(data, reference_date) else 1.0
        media_kit_missing = 0.0 if self._has_usable_media_kit(data) else 1.0
        components = [
            Component("content_gap", 0.35, self._content_gap_value(data, reference_date)),
            Component("report_due", 0.20, report_due),
            Component("media_kit_missing", 0.20, media_kit_missing),
            Component("timing_relevance", 0.25, self._timing_relevance(data, reference_date)),
        ]
        return self._scored("content_opportunity_score", components)

    def _risk(
        self, data: CampaignDataBundle, reference_date: date | None
    ) -> tuple[int | None, Explanation | None, Warning | None]:
        if data.campaign is None and data.smart_link_stats is None:
            return (
                None,
                None,
                self._unknown("risk_score", "no campaign data or smart-link statistics"),
            )

        campaign = data.campaign
        status = (campaign.status or "").lower() if campaign else ""
        is_active = status == _ACTIVE_CAMPAIGN_STATUS
        has_content = bool(self._completed_outputs(data))
        stats = data.smart_link_stats
        link_active = stats is not None and self._smart_link_has_activity(stats)

        no_traction = 1.0 if (is_active and not has_content and not link_active) else 0.0
        content_gap_active = 1.0 if (is_active and not has_content) else 0.0
        overdue = 1.0 if self._is_overdue(campaign, status, reference_date) else 0.0
        data_quality = 1.0 if self._has_quality_issues(data) else 0.0

        components = [
            Component("no_traction", 0.35, no_traction),
            Component("link_inactivity", 0.20, self._link_inactivity_value(stats)),
            Component("content_gap_active", 0.15, content_gap_active),
            Component("overdue", 0.15, overdue),
            Component("data_quality", 0.15, data_quality),
        ]
        return self._scored("risk_score", components)

    # --- composites: priority and grade ----------------------------------------

    def _priority(
        self,
        readiness: int | None,
        momentum: int | None,
        opportunity: int | None,
        risk: int | None,
    ) -> tuple[int | None, Explanation | None, Warning | None]:
        available = [
            (key, PRIORITY_WEIGHTS[key], value)
            for key, value in (
                ("content_opportunity_score", opportunity),
                ("momentum_score", momentum),
                ("risk_score", risk),
                ("campaign_readiness_score", readiness),
            )
            if value is not None
        ]
        if len(available) < 2:
            return (
                None,
                None,
                self._unknown("priority_score", "fewer than two component scores available"),
            )

        total_weight = sum(weight for _, weight, _ in available)
        value = round(sum(weight * score for _, weight, score in available) / total_weight)
        breakdown = ", ".join(f"{key} w{weight:.2f} v{score}" for key, weight, score in available)
        message = (
            f"priority_score={value}/100 — weighted blend of [{breakdown}] "
            "(weights renormalised over available scores; risk raises priority)."
        )
        return value, Explanation(code="priority_score", message=message, weight=None), None

    def _grade(
        self,
        readiness: int | None,
        momentum: int | None,
        risk: int | None,
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> Grade:
        inputs = [
            ("readiness", STANDING_WEIGHTS["readiness"], readiness),
            ("momentum", STANDING_WEIGHTS["momentum"], momentum),
            (
                "risk_inverted",
                STANDING_WEIGHTS["risk_inverted"],
                (100 - risk) if risk is not None else None,
            ),
        ]
        available = [(key, weight, value) for key, weight, value in inputs if value is not None]
        if not available:
            warnings.append(self._unknown("grade", "no readiness, momentum or risk score"))
            return "unknown"

        total_weight = sum(weight for _, weight, _ in available)
        standing = round(sum(weight * value for _, weight, value in available) / total_weight)
        grade = _grade_for(standing)
        breakdown = ", ".join(f"{key} w{weight:.2f} v{value}" for key, weight, value in available)
        explanations.append(
            Explanation(
                code="grade",
                message=(
                    f"grade={grade} (overall_standing={standing}/100) — weighted blend of "
                    f"[{breakdown}] (renormalised over available scores)."
                ),
                weight=None,
            )
        )
        return grade

    # --- value helpers ---------------------------------------------------------

    def _recent_content_value(self, data: CampaignDataBundle, reference_date: date | None) -> float:
        completed = self._completed_outputs(data)
        if not completed:
            return 0.0
        if reference_date is None:
            # Present, but recency cannot be assessed without the wall clock.
            return 0.5
        cutoff = reference_date - timedelta(days=RECENT_CONTENT_WINDOW_DAYS)
        recent = sum(
            1
            for output in completed
            if output.created_at and cutoff <= output.created_at <= reference_date
        )
        return _saturate(recent, MOMENTUM_RECENT_OUTPUTS_SATURATION)

    def _content_gap_value(self, data: CampaignDataBundle, reference_date: date | None) -> float:
        completed = self._completed_outputs(data)
        if not completed:
            return 1.0
        if reference_date is None:
            # Content exists but staleness is unknown: a mild standing gap.
            return 0.2
        cutoff = reference_date - timedelta(days=RECENT_CONTENT_WINDOW_DAYS)
        has_recent = any(
            output.created_at and cutoff <= output.created_at <= reference_date
            for output in completed
        )
        return 0.0 if has_recent else 0.4

    def _timing_relevance(self, data: CampaignDataBundle, reference_date: date | None) -> float:
        track = data.track
        if (
            track is not None
            and track.release_date is not None
            and reference_date is not None
            and abs((track.release_date - reference_date).days) <= RELEASE_WINDOW_DAYS
        ):
            return 1.0
        status = (data.campaign.status or "").lower() if data.campaign else ""
        return {"active": 0.6, "scheduled": 0.5, "paused": 0.3}.get(status, 0.0)

    def _link_inactivity_value(self, stats: SmartLinkStats | None) -> float:
        if stats is None:
            # Unknown traction is not a penalty (mirrors the analysis service).
            return 0.0
        clicks = self._clamped_clicks(stats)
        has_clicks = clicks["7d"] > 0 or clicks["30d"] > 0 or clicks["total"] > 0
        has_links = max(stats.active_links or 0, 0) > 0
        if has_clicks:
            return 0.0
        return 0.5 if has_links else 1.0

    @staticmethod
    def _is_overdue(campaign, status: str, reference_date: date | None) -> bool:
        return bool(
            campaign
            and campaign.end_date
            and reference_date
            and campaign.end_date < reference_date
            and status not in _FINISHED_CAMPAIGN_STATUSES
        )

    def _has_quality_issues(self, data: CampaignDataBundle) -> bool:
        campaign = data.campaign
        inconsistent_dates = bool(
            campaign
            and campaign.start_date
            and campaign.end_date
            and campaign.end_date < campaign.start_date
        )
        stats = data.smart_link_stats
        negative_stats = stats is not None and self._smart_link_has_negative(stats)
        return inconsistent_dates or negative_stats

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
                    message="Smart-link statistics contain negative values; clamped to zero.",
                )
            )

        if reference_date is not None:
            future = sum(
                1
                for output in data.content_outputs
                if output.created_at and output.created_at > reference_date
            )
            if future:
                warnings.append(
                    Warning(
                        code="future_content_output_date",
                        message=(
                            f"{future} content output(s) are dated after the reference date; "
                            "excluded from recency scoring."
                        ),
                    )
                )

    # --- small deterministic helpers -------------------------------------------

    @staticmethod
    def _scored(code: str, components: list[Component]) -> tuple[int, Explanation, None]:
        value = _to_score(components)
        breakdown = ", ".join(f"{c.key} w{c.weight:.2f} v{c.value:.2f}" for c in components)
        message = f"{code}={value}/100 — weighted components: [{breakdown}]."
        weight = PRIORITY_WEIGHTS.get(code)
        return value, Explanation(code=code, message=message, weight=weight), None

    @staticmethod
    def _unknown(code: str, reason: str) -> Warning:
        return Warning(
            code=f"{code}_unknown",
            message=f"{code} not computed: {reason}.",
            details={"score": code},
        )

    @staticmethod
    def _collect(
        outcome: tuple[int | None, Explanation | None, Warning | None],
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> int | None:
        value, explanation, warning = outcome
        if explanation is not None:
            explanations.append(explanation)
        if warning is not None:
            warnings.append(warning)
        return value

    @staticmethod
    def _clamped_clicks(stats: SmartLinkStats | None) -> dict[str, int]:
        """Non-negative click counters (None → 0, negatives → 0)."""
        if stats is None:
            return {"7d": 0, "30d": 0, "total": 0}
        return {
            "7d": max(stats.clicks_last_7_days or 0, 0),
            "30d": max(stats.clicks_last_30_days or 0, 0),
            "total": max(stats.total_clicks or 0, 0),
        }

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
    def _completed_outputs(data: CampaignDataBundle) -> list:
        return [
            output
            for output in data.content_outputs
            if (output.status or "").lower() in _COMPLETED_OUTPUT_STATUSES
        ]

    @staticmethod
    def _has_usable_media_kit(data: CampaignDataBundle) -> bool:
        return any(
            (kit.status or "").lower() in _USABLE_MEDIA_KIT_STATUSES for kit in data.media_kits
        )

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
            # A completed report exists but recency cannot/need not be assessed.
            return True
        return any(
            (reference_date - period_end).days <= REPORT_DUE_AFTER_DAYS for period_end in dated
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
        request: ScoringRequest,
        result: ScoringResult,
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> ScoringResponse:
        # `generated_at` is intentionally left unset to preserve determinism;
        # timestamping is the Backend Core's concern.
        return ScoringResponse(
            request_id=request.request_id,
            workspace_id=request.workspace_id,
            result=result,
            explanations=explanations,
            warnings=warnings,
            metadata=ResponseMetadata(payload_version=request.payload_version),
        )


def _saturate(value: float, saturation: float) -> float:
    """Map a non-negative count/value to [0, 1], reaching 1.0 at `saturation`."""
    if value <= 0:
        return 0.0
    return min(value / saturation, 1.0)


def _to_score(components: list[Component]) -> int:
    """Weighted sum of components (weights sum to 1.0) → an int in [0, 100]."""
    raw = sum(component.weight * component.value for component in components)
    return max(0, min(100, round(100 * raw)))


def _grade_for(standing: int) -> Grade:
    for threshold, grade in GRADE_THRESHOLDS:
        if standing >= threshold:
            return grade
    return "D"


# Module-level singleton (the engine is stateless).
scoring_engine = ScoringEngine()
