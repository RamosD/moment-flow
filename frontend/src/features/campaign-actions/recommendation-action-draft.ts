/**
 * Builds a frontend-only action draft from a flexible intelligence
 * recommendation. The draft now carries the safe correlation context required
 * by the persistent CampaignAction create flow; the draft itself is never
 * persisted.
 *
 * The recommendation contract is explicitly NOT guaranteed (see
 * `entities/campaign/intelligence.ts`): fields may be missing, renamed, or of
 * an unexpected type. Every read below is defensive and never throws.
 */

import type { CampaignRecommendation } from '@/entities/campaign'
import type {
  CampaignActionPriority,
  CampaignActionSource,
  RecommendationRef,
} from '@/entities/campaign-action'
import type { Metadata } from '@/shared/types'

import type { ArtifactCampaignActionType } from './action-type-options'
import { buildRecommendationCampaignActionContext } from './recommendation-snapshot'

export interface RecommendationActionDraft {
  recommendationRef: RecommendationRef
  recommendationSnapshot: Metadata
  title: string
  description: string | null
  priority: CampaignActionPriority
  /** Raw confidence value from the recommendation, if numeric. Not normalized. */
  confidence: number | null
  /**
   * Best-effort guess, restricted to supported campaign action types —
   * suggesting an unsupported type would be misleading since it could never
   * be created. `null` when no keyword signal matches.
   */
  suggestedActionType: ArtifactCampaignActionType | null
  source: CampaignActionSource
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    const str = asString(value)
    if (str) return str
  }
  return null
}

function readConfidence(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

/** Keyword → supported action type. Best-effort; unmatched stays `null`. */
const TYPE_KEYWORDS: ReadonlyArray<[RegExp, ArtifactCampaignActionType]> = [
  [/report/i, 'report_request'],
  [/media[_\s-]?kit/i, 'media_kit_request'],
  [/content[_\s-]?pack|asset|content/i, 'content_pack'],
]

function suggestActionType(
  recommendation: CampaignRecommendation,
): ArtifactCampaignActionType | null {
  const signal = firstString(
    recommendation.action,
    recommendation.type,
    recommendation.title,
    recommendation.label,
  )
  if (!signal) return null
  for (const [pattern, type] of TYPE_KEYWORDS) {
    if (pattern.test(signal)) return type
  }
  return null
}

/**
 * Build a draft from a recommendation. Tolerates any subset of fields being
 * present or absent — never throws on missing/malformed data — so the UI can
 * always offer a "Create action" affordance, even for sparse recommendations.
 */
export function buildRecommendationActionDraft(
  campaignId: string,
  recommendation: CampaignRecommendation | undefined,
  index: number,
): RecommendationActionDraft {
  const rec = recommendation ?? {}
  const context = buildRecommendationCampaignActionContext(
    campaignId,
    recommendation,
    index,
  )

  return {
    recommendationRef: context.recommendationRef,
    recommendationSnapshot: context.recommendationSnapshot,
    title: firstString(rec.title, rec.label, rec.action) ?? 'Recommendation',
    description: firstString(rec.description, rec.reason),
    priority: context.priority,
    confidence: readConfidence(rec.confidence),
    suggestedActionType: suggestActionType(rec),
    source: 'recommendation',
  }
}
