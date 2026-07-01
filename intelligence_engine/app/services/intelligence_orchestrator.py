"""Composite intelligence orchestration (IE-008).

`POST /intelligence/campaign` runs the four existing engines and aggregates
their results into a single coherent diagnostic:

    analysis (IE-004) · scoring (IE-005) · moment detection (IE-007) ·
    recommendations (IE-006)

Design
------
- **Orchestration, not re-implementation.** The orchestrator owns no scoring
  or detection logic of its own; it calls the existing stateless services
  through their public contracts and stitches the outputs together. Each
  service stays independently testable.
- **Resilient by section.** Every stage runs inside `_safe`: a *predictable*
  partial failure (an unexpected exception in one stage over otherwise-valid,
  schema-checked input) is converted into a `<stage>_unavailable` warning and a
  defaulted section, never a 500. Payload validation still happens upstream in
  FastAPI, so malformed payloads remain a normalised 422.
- **Consolidated, deduplicated explanations/warnings.** Envelope-level
  explanations and warnings from every stage are merged and de-duplicated by
  `code` (first occurrence wins), in a fixed stage order, so the consolidated
  lists are deterministic and noise-free (e.g. a single `insufficient_data`).
- **Deterministic.** No wall clock, no persistence, no Backend Core or renderer
  calls. `metadata.generated_at` stays unset.

The per-recommendation and per-moment explanations remain inside the
`recommendations`/`moments` objects; the envelope's consolidated `explanations`
hold the analysis and scoring rationale.
"""

from collections.abc import Callable
from typing import TypeVar

from app.schemas.campaign import CampaignAnalysisRequest, CampaignAnalysisResult
from app.schemas.common import Explanation, Grade, Warning
from app.schemas.intelligence import (
    IntelligenceCampaignRequest,
    IntelligenceCampaignResponse,
    IntelligenceResult,
)
from app.schemas.moments import Moment, MomentsRequest
from app.schemas.recommendations import Recommendation, RecommendationsRequest
from app.schemas.responses import IntelligenceResponse, ResponseMetadata
from app.schemas.scoring import ScoreSet, ScoringRequest
from app.services.campaign_analysis import campaign_analysis_service
from app.services.moment_detector import moment_detector
from app.services.recommendation_engine import recommendation_engine
from app.services.scoring_engine import scoring_engine

T = TypeVar("T")


class IntelligenceOrchestrator:
    """Stateless composite orchestrator. Safe to share as a singleton."""

    def run(self, request: IntelligenceCampaignRequest) -> IntelligenceCampaignResponse:
        # Validate once, reuse for every sub-request (all are CampaignRequest
        # subclasses with the identical shape — this goes through the public
        # contract, not service internals).
        payload = request.model_dump()
        warnings: list[Warning] = []

        analysis_resp = self._safe(
            lambda: campaign_analysis_service.analyse(
                CampaignAnalysisRequest.model_validate(payload)
            ),
            "analysis",
            warnings,
        )
        scoring_resp = self._safe(
            lambda: scoring_engine.score(ScoringRequest.model_validate(payload)),
            "scoring",
            warnings,
        )
        moments_resp = self._safe(
            lambda: moment_detector.detect(MomentsRequest.model_validate(payload)),
            "moments",
            warnings,
        )
        recs_resp = self._safe(
            lambda: recommendation_engine.recommend(RecommendationsRequest.model_validate(payload)),
            "recommendations",
            warnings,
        )

        analysis: CampaignAnalysisResult = (
            analysis_resp.result if analysis_resp else CampaignAnalysisResult()
        )
        scores: ScoreSet = scoring_resp.result.scores if scoring_resp else ScoreSet()
        grade: Grade = scoring_resp.result.grade if scoring_resp else "unknown"
        moments: list[Moment] = moments_resp.result.moments if moments_resp else []
        recommendations: list[Recommendation] = (
            recs_resp.result.recommendations if recs_resp else []
        )

        # Consolidate explanations/warnings across stages (fixed order; dedup by code).
        explanations: list[Explanation] = []
        for resp in (analysis_resp, scoring_resp, moments_resp, recs_resp):
            if resp is not None:
                explanations.extend(resp.explanations)
                warnings.extend(resp.warnings)

        result = IntelligenceResult(
            analysis=analysis,
            scores=scores,
            grade=grade,
            moments=moments,
            recommendations=recommendations,
            summary=self._summary(analysis, scores, grade, moments, recommendations),
        )
        return self._build(
            request,
            result,
            self._dedup_by_code(explanations),
            self._dedup_by_code(warnings),
        )

    # --- helpers ---------------------------------------------------------------

    @staticmethod
    def _safe(run_stage: Callable[[], T], stage: str, warnings: list[Warning]) -> T | None:
        """Run one stage; convert a predictable failure into a warning, not a 500."""
        try:
            return run_stage()
        except Exception:
            # A composite must degrade gracefully: one failing stage becomes a
            # warning + omitted section, never a 500 for the whole diagnostic.
            warnings.append(
                Warning(
                    code=f"{stage}_unavailable",
                    message=f"The {stage} stage could not be completed; its section was omitted.",
                    details={"stage": stage},
                )
            )
            return None

    @staticmethod
    def _summary(
        analysis: CampaignAnalysisResult,
        scores: ScoreSet,
        grade: Grade,
        moments: list[Moment],
        recommendations: list[Recommendation],
    ) -> str:
        def fmt(value: int | None) -> str:
            return "n/a" if value is None else str(value)

        top_action = f", top action {recommendations[0].action}" if recommendations else ""
        return (
            f"Campaign health '{analysis.campaign_health}', grade {grade}. "
            f"Scores — readiness {fmt(scores.campaign_readiness_score)}, "
            f"momentum {fmt(scores.momentum_score)}, "
            f"opportunity {fmt(scores.content_opportunity_score)}, "
            f"risk {fmt(scores.risk_score)}, "
            f"priority {fmt(scores.priority_score)}. "
            f"{len(moments)} moment(s) detected; "
            f"{len(recommendations)} recommendation(s){top_action}."
        )

    @staticmethod
    def _dedup_by_code(items: list[T]) -> list[T]:
        """First occurrence per `code` wins; order preserved (deterministic)."""
        seen: set[str] = set()
        deduped: list[T] = []
        for item in items:
            code = item.code  # type: ignore[attr-defined]
            if code not in seen:
                seen.add(code)
                deduped.append(item)
        return deduped

    @staticmethod
    def _build(
        request: IntelligenceCampaignRequest,
        result: IntelligenceResult,
        explanations: list[Explanation],
        warnings: list[Warning],
    ) -> IntelligenceCampaignResponse:
        # `generated_at` is intentionally left unset to preserve determinism;
        # timestamping is the Backend Core's concern.
        return IntelligenceResponse[IntelligenceResult](
            request_id=request.request_id,
            workspace_id=request.workspace_id,
            result=result,
            explanations=explanations,
            warnings=warnings,
            metadata=ResponseMetadata(payload_version=request.payload_version),
        )


# Module-level singleton (the orchestrator is stateless).
intelligence_orchestrator = IntelligenceOrchestrator()
