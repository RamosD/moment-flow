"""Deterministic, explainable campaign recommendations (IE-006).

No generative AI, no external calls, no persistence — and, critically, **no
side effects on the product**: a recommendation only ever *suggests* an action
(plus, when relevant, a content pack and the outputs it would produce). It never
creates Django entities and never calls the renderer. This honours the
architectural thesis:

    Intelligence recommends → Django decides and creates jobs → Renderer renders.

Low coupling
------------
The engine reuses the existing **scoring** engine through its public output
only (`ScoreSet`): scores drive priority/confidence and the "healthy → no
action" decision. The specific content triggers (release window, milestone,
weekly growth, missing media kit, report due, smart-link inactivity) are read
straight from the shared campaign data bundle. We do not import any private
helpers from the scoring or analysis services, nor depend on their internals.

Product-supportability (risk IE-RSK-005)
----------------------------------------
Every `suggested_content_pack` and every `expected_outputs.template_key` is
drawn from the seeded product catalogue in
`backend_core/apps/content/seeds.py` (mirrored here as constants, kept in sync
manually — we never import Django). So the engine never recommends something
the product cannot fulfil. The `ContentPackKey`/`OutputType` Literals enforce
the vocabulary at the schema level as a second line of defence.

Determinism and time
--------------------
Time-based rules (release window, report recency) are anchored to
`context["reference_date"]` (ISO `YYYY-MM-DD`); without it they degrade to
presence-based behaviour rather than reading the wall clock. The same input
always produces the same ordered list of recommendations.

Rules (each fires independently; results are sorted by priority, then
confidence, then action name)
-----------------------------------------------------------------------------
- insufficient data (all scores null) → `wait_for_more_data` (+ warning)
- release window / release-type campaign → `create_release_post`
- milestone goal achieved / milestone campaign / clicks threshold → `create_milestone_post`
- weekly-growth campaign / weekly click signal → `create_weekly_growth_post`
- no usable media kit → `create_media_kit`
- no recent report (with substance to report on) → `create_report`
- active campaign with smart-link activity → `create_story`
- smart-link configured but inactive → `improve_smart_link`
- nothing triggered, data sufficient → `no_action`
"""

from datetime import date

from app.schemas.campaign import CampaignDataBundle, SmartLinkStats
from app.schemas.common import Explanation, Priority, Warning
from app.schemas.recommendations import (
    ExpectedOutput,
    Recommendation,
    RecommendationsRequest,
    RecommendationsResponse,
    RecommendationsResult,
)
from app.schemas.responses import ResponseMetadata
from app.schemas.scoring import ScoreSet, ScoringRequest
from app.services.scoring_engine import scoring_engine

# --- Documented thresholds (deterministic; no wall-clock dependency) ----------

RELEASE_WINDOW_DAYS = 14
REPORT_DUE_AFTER_DAYS = 30
MILESTONE_CLICKS_THRESHOLD = 1000
WEEKLY_GROWTH_CLICKS_THRESHOLD = 20

# --- Seeded product catalogue (mirrors backend_core/apps/content/seeds.py) -----
# Kept in sync manually; the engine only ever suggests values from this set so
# every recommendation is fulfilment-ready (IE-RSK-005).

PACK_RELEASE = "release_pack"
PACK_MILESTONE = "milestone_pack"
PACK_WEEKLY_GROWTH = "weekly_growth_pack"
PACK_MEDIA_KIT = "auto_media_kit"

SUPPORTED_PACKS = frozenset({PACK_RELEASE, PACK_MILESTONE, PACK_WEEKLY_GROWTH, PACK_MEDIA_KIT})
SUPPORTED_TEMPLATE_KEYS = frozenset(
    {
        "system_post",
        "system_story",
        "system_carousel",
        "system_thumbnail",
        "system_report",
        "system_media_kit",
    }
)

# --- Campaign vocabularies (mirror backend_core/apps/campaigns/models.py) ------

_RELEASE_CAMPAIGN_TYPES = {"single_release", "music_video_release", "album_release"}
_FINISHED_CAMPAIGN_STATUSES = {"completed", "archived"}
_COMPLETED_OUTPUT_STATUSES = {"completed"}
_COMPLETED_REPORT_STATUSES = {"completed"}
_USABLE_MEDIA_KIT_STATUSES = {"generated", "published"}

# --- Per-rule confidence (deterministic; documented, never random) ------------

CONFIDENCE: dict[str, float] = {
    "release_window": 0.85,
    "release_type": 0.70,
    "milestone_goal": 0.80,
    "milestone_type": 0.75,
    "milestone_clicks": 0.65,
    "weekly_type": 0.75,
    "weekly_signal": 0.65,
    "media_kit": 0.70,
    "report": 0.70,
    "story": 0.60,
    "improve_smart_link": 0.70,
    "no_action": 0.50,
    "wait": 0.30,
}

_PRIORITY_RANK: dict[Priority, int] = {"high": 0, "medium": 1, "low": 2}


def _post() -> ExpectedOutput:
    return ExpectedOutput(output_type="post", format="png", template_key="system_post")


def _story_output() -> ExpectedOutput:
    return ExpectedOutput(output_type="story", format="png", template_key="system_story")


def _carousel() -> ExpectedOutput:
    return ExpectedOutput(output_type="carousel", format="png", template_key="system_carousel")


def _media_kit_output() -> ExpectedOutput:
    return ExpectedOutput(output_type="media_kit", format="pdf", template_key="system_media_kit")


def _report_output() -> ExpectedOutput:
    return ExpectedOutput(output_type="report", format="pdf", template_key="system_report")


class RecommendationEngine:
    """Stateless heuristic recommender. Safe to share as a singleton."""

    def recommend(self, request: RecommendationsRequest) -> RecommendationsResponse:
        data = request.data
        reference_date = self._parse_reference_date(request.context)

        # Reuse the scoring engine via its public contract only (low coupling).
        scoring = scoring_engine.score(ScoringRequest.model_validate(request.model_dump()))
        scores = scoring.result.scores
        # Carry over consistency/data-quality warnings; drop scoring-internal
        # `*_unknown` and `insufficient_data` (handled explicitly below).
        warnings = [w for w in scoring.warnings if w.code in _CARRIED_WARNING_CODES]

        if self._is_insufficient(scores):
            warnings.append(
                Warning(
                    code="insufficient_data",
                    message="Not enough campaign data to recommend an action yet.",
                )
            )
            result = RecommendationsResult(recommendations=[self._wait_for_more_data()])
            return self._build(request, result, self._envelope_explanations(scores), warnings)

        recommendations: list[Recommendation] = []
        self._maybe(recommendations, self._release(data, reference_date))
        self._maybe(recommendations, self._milestone(data))
        weekly = self._weekly_growth(data)
        self._maybe(recommendations, weekly)
        self._maybe(recommendations, self._media_kit(data))
        self._maybe(recommendations, self._report(data, reference_date))
        self._maybe(recommendations, self._story(data, weekly_fired=weekly is not None))
        self._maybe(recommendations, self._improve_smart_link(data))

        if not recommendations:
            recommendations.append(self._no_action())

        recommendations = self._sorted(recommendations)
        result = RecommendationsResult(recommendations=recommendations)
        return self._build(request, result, self._envelope_explanations(scores), warnings)

    # --- content rules ---------------------------------------------------------

    def _release(self, data: CampaignDataBundle, ref: date | None) -> Recommendation | None:
        if data.campaign is None or self._status(data) in _FINISHED_CAMPAIGN_STATUSES:
            return None
        in_window = self._in_release_window(data, ref)
        is_release_campaign = self._campaign_type(data) in _RELEASE_CAMPAIGN_TYPES and self._status(
            data
        ) in {"active", "scheduled"}
        if not (in_window or is_release_campaign):
            return None
        if in_window:
            priority: Priority = "high"
            confidence = CONFIDENCE["release_window"]
            signal = Explanation(
                code="release_window",
                message="The track release date is within the release window.",
            )
        else:
            priority = "medium"
            confidence = CONFIDENCE["release_type"]
            signal = Explanation(
                code="release_campaign_active",
                message=f"Release-type campaign ({self._campaign_type(data)}) is "
                f"{self._status(data)}.",
            )
        return Recommendation(
            action="create_release_post",
            priority=priority,
            confidence=confidence,
            reason="The campaign is in its release moment; publish a release post.",
            suggested_content_pack=PACK_RELEASE,
            expected_outputs=[_post()],
            explanations=[signal],
        )

    def _milestone(self, data: CampaignDataBundle) -> Recommendation | None:
        if data.campaign is None or self._status(data) in _FINISHED_CAMPAIGN_STATUSES:
            return None
        achieved_goal = any(
            isinstance(goal, dict)
            and goal.get("goal_type") == "milestone"
            and goal.get("status") == "achieved"
            for goal in data.goals
        )
        clicks = self._total_clicks(data.smart_link_stats)
        if achieved_goal:
            priority: Priority = "high"
            confidence = CONFIDENCE["milestone_goal"]
            signal = Explanation(
                code="milestone_goal_achieved",
                message="A milestone goal has been achieved.",
            )
        elif self._campaign_type(data) == "milestone_campaign":
            priority = "high"
            confidence = CONFIDENCE["milestone_type"]
            signal = Explanation(
                code="milestone_campaign_type",
                message="Campaign type is milestone_campaign.",
            )
        elif clicks >= MILESTONE_CLICKS_THRESHOLD:
            priority = "medium"
            confidence = CONFIDENCE["milestone_clicks"]
            signal = Explanation(
                code="milestone_click_threshold",
                message=(
                    f"Smart-link total clicks ({clicks}) crossed the milestone threshold "
                    f"({MILESTONE_CLICKS_THRESHOLD})."
                ),
            )
        else:
            return None
        return Recommendation(
            action="create_milestone_post",
            priority=priority,
            confidence=confidence,
            reason="The campaign reached a milestone worth celebrating.",
            suggested_content_pack=PACK_MILESTONE,
            expected_outputs=[_post(), _carousel()],
            explanations=[signal],
        )

    def _weekly_growth(self, data: CampaignDataBundle) -> Recommendation | None:
        if data.campaign is None or self._status(data) != "active":
            return None
        clicks_7d = self._clicks_7d(data.smart_link_stats)
        if self._campaign_type(data) == "weekly_growth_campaign":
            confidence = CONFIDENCE["weekly_type"]
            signal = Explanation(
                code="weekly_growth_campaign_type",
                message="Campaign type is weekly_growth_campaign.",
            )
        elif clicks_7d >= WEEKLY_GROWTH_CLICKS_THRESHOLD:
            confidence = CONFIDENCE["weekly_signal"]
            signal = Explanation(
                code="weekly_growth_signal",
                message=(
                    f"Smart-link clicks in the last 7 days ({clicks_7d}) cleared the weekly "
                    f"growth threshold ({WEEKLY_GROWTH_CLICKS_THRESHOLD})."
                ),
            )
        else:
            return None
        return Recommendation(
            action="create_weekly_growth_post",
            priority="medium",
            confidence=confidence,
            reason="The campaign shows weekly growth worth highlighting.",
            suggested_content_pack=PACK_WEEKLY_GROWTH,
            expected_outputs=[_post(), _story_output()],
            explanations=[signal],
        )

    def _media_kit(self, data: CampaignDataBundle) -> Recommendation | None:
        if data.campaign is None or self._has_usable_media_kit(data):
            return None
        status = self._status(data)
        is_media_campaign = self._campaign_type(data) == "media_campaign"
        # A media kit needs a campaign with substance: skip brand-new drafts.
        if status == "draft" and not is_media_campaign:
            return None
        return Recommendation(
            action="create_media_kit",
            priority="high" if is_media_campaign else "medium",
            confidence=CONFIDENCE["media_kit"],
            reason="The campaign has no media kit; generate one for outreach.",
            suggested_content_pack=PACK_MEDIA_KIT,
            expected_outputs=[_media_kit_output()],
            explanations=[
                Explanation(
                    code="media_kit_missing",
                    message="No generated or published media kit exists for the campaign.",
                )
            ],
        )

    def _report(self, data: CampaignDataBundle, ref: date | None) -> Recommendation | None:
        if data.campaign is None:
            return None
        status = self._status(data)
        if status not in {"active", "completed", "paused"}:
            return None
        if self._has_recent_completed_report(data, ref):
            return None
        # Only worth reporting once there is something to report on.
        has_substance = (
            bool(self._completed_outputs(data))
            or self._smart_link_has_activity(data.smart_link_stats)
            or status == "completed"
        )
        if not has_substance:
            return None
        return Recommendation(
            action="create_report",
            priority="medium",
            confidence=CONFIDENCE["report"],
            reason="No recent report is available; generate a campaign report.",
            expected_outputs=[_report_output()],
            explanations=[
                Explanation(
                    code="report_due",
                    message="There is no recent completed report for the campaign.",
                )
            ],
        )

    def _story(self, data: CampaignDataBundle, *, weekly_fired: bool) -> Recommendation | None:
        # Skip when the weekly-growth post (which already includes a story) fired.
        if weekly_fired or self._status(data) != "active":
            return None
        if not self._smart_link_has_activity(data.smart_link_stats):
            return None
        return Recommendation(
            action="create_story",
            priority="low",
            confidence=CONFIDENCE["story"],
            reason="The active campaign has smart-link activity; post a story to sustain it.",
            expected_outputs=[_story_output()],
            explanations=[
                Explanation(
                    code="engagement_opportunity",
                    message="Active campaign with positive smart-link activity.",
                )
            ],
        )

    def _improve_smart_link(self, data: CampaignDataBundle) -> Recommendation | None:
        stats = data.smart_link_stats
        if stats is None or self._smart_link_has_activity(stats):
            return None
        active = self._status(data) == "active"
        return Recommendation(
            action="improve_smart_link",
            priority="high" if active else "medium",
            confidence=CONFIDENCE["improve_smart_link"],
            reason="Smart links are configured but show no activity; improve them.",
            explanations=[
                Explanation(
                    code="smart_link_inactive",
                    message="Smart-link statistics are present but show no clicks or active links.",
                )
            ],
        )

    # --- terminal recommendations ---------------------------------------------

    def _no_action(self) -> Recommendation:
        return Recommendation(
            action="no_action",
            priority="low",
            confidence=CONFIDENCE["no_action"],
            reason="The campaign looks healthy; no campaign action is needed right now.",
            explanations=[
                Explanation(
                    code="campaign_healthy",
                    message="No release, milestone, growth, content or smart-link trigger fired.",
                )
            ],
        )

    def _wait_for_more_data(self) -> Recommendation:
        return Recommendation(
            action="wait_for_more_data",
            priority="low",
            confidence=CONFIDENCE["wait"],
            reason="There is not enough campaign data to recommend an action yet.",
            explanations=[
                Explanation(
                    code="insufficient_data",
                    message="No score could be computed from the provided data.",
                )
            ],
        )

    # --- helpers ---------------------------------------------------------------

    @staticmethod
    def _maybe(bucket: list[Recommendation], rec: Recommendation | None) -> None:
        if rec is not None:
            bucket.append(rec)

    @staticmethod
    def _sorted(recommendations: list[Recommendation]) -> list[Recommendation]:
        # Stable, deterministic ordering: priority, then confidence (desc), then
        # action name (so ties never depend on rule evaluation order).
        return sorted(
            recommendations,
            key=lambda rec: (_PRIORITY_RANK[rec.priority], -rec.confidence, rec.action),
        )

    @staticmethod
    def _envelope_explanations(scores: ScoreSet) -> list[Explanation]:
        return [
            Explanation(
                code="scoring_basis",
                message=(
                    "Recommendations derived from scores — "
                    f"readiness={scores.campaign_readiness_score}, "
                    f"momentum={scores.momentum_score}, "
                    f"opportunity={scores.content_opportunity_score}, "
                    f"risk={scores.risk_score}, priority={scores.priority_score}."
                ),
            )
        ]

    @staticmethod
    def _is_insufficient(scores: ScoreSet) -> bool:
        return all(
            value is None
            for value in (
                scores.campaign_readiness_score,
                scores.momentum_score,
                scores.content_opportunity_score,
                scores.risk_score,
                scores.priority_score,
            )
        )

    @staticmethod
    def _status(data: CampaignDataBundle) -> str:
        return (data.campaign.status or "").lower() if data.campaign else ""

    @staticmethod
    def _campaign_type(data: CampaignDataBundle) -> str:
        return (data.campaign.campaign_type or "").lower() if data.campaign else ""

    @staticmethod
    def _in_release_window(data: CampaignDataBundle, ref: date | None) -> bool:
        track = data.track
        if track is None or track.release_date is None or ref is None:
            return False
        return abs((track.release_date - ref).days) <= RELEASE_WINDOW_DAYS

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
    def _parse_reference_date(context: dict) -> date | None:
        raw = context.get("reference_date")
        if isinstance(raw, date):
            return raw
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None
        return None

    @staticmethod
    def _build(
        request: RecommendationsRequest,
        result: RecommendationsResult,
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> RecommendationsResponse:
        # `generated_at` is intentionally left unset to preserve determinism;
        # timestamping is the Backend Core's concern.
        return RecommendationsResponse(
            request_id=request.request_id,
            workspace_id=request.workspace_id,
            result=result,
            explanations=explanations,
            warnings=warnings,
            metadata=ResponseMetadata(payload_version=request.payload_version),
        )


# Consistency/data-quality warnings worth surfacing to the recommendation caller
# (the scoring-internal `*_unknown` and `insufficient_data` are handled here).
_CARRIED_WARNING_CODES = frozenset(
    {
        "inconsistent_campaign_dates",
        "negative_smart_link_stats",
        "future_content_output_date",
        "invalid_reference_date",
    }
)


# Module-level singleton (the engine is stateless).
recommendation_engine = RecommendationEngine()
