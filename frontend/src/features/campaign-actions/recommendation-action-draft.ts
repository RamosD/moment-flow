/**
 * Builds a frontend-only "action draft" from a flexible intelligence
 * recommendation. A draft is an intent, never persisted on its own — only
 * `createCampaignAction` (entities/campaign-action, CA-003) turns it into a
 * real Backend Core artifact once the user confirms a "Create action" form
 * (CA-007, not implemented yet).
 *
 * The recommendation contract is explicitly NOT guaranteed (see
 * `entities/campaign/intelligence.ts`): fields may be missing, renamed, or of
 * an unexpected type. Every read below is defensive and never throws.
 */

import type { CampaignRecommendation } from '@/entities/campaign'
import { deriveRecommendationRef } from '@/entities/campaign-action'
import type {
  CampaignActionSource,
  RecommendationLike,
  RecommendationRef,
  SupportedCampaignActionType,
} from '@/entities/campaign-action'

export interface RecommendationActionDraft {
  recommendationRef: RecommendationRef
  title: string
  description: string | null
  priority: string | null
  /** Raw confidence value from the recommendation, if numeric. Not normalized. */
  confidence: number | null
  /**
   * Best-effort guess, restricted to supported campaign action types —
   * suggesting an unsupported type would be misleading since it could never
   * be created. `null` when no keyword signal matches.
   */
  suggestedActionType: SupportedCampaignActionType | null
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

function readPriority(value: unknown): string | null {
  if (typeof value === 'number') return `Priority ${value}`
  return asString(value) ?? null
}

function readConfidence(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

/** Keyword → supported action type. Best-effort; unmatched stays `null`. */
const TYPE_KEYWORDS: ReadonlyArray<[RegExp, SupportedCampaignActionType]> = [
  [/report/i, 'report_request'],
  [/media[_\s-]?kit/i, 'media_kit_request'],
  [/content[_\s-]?pack|asset|content/i, 'content_pack'],
]

function suggestActionType(
  recommendation: CampaignRecommendation,
): SupportedCampaignActionType | null {
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

/** Narrow a recommendation down to the fields {@link deriveRecommendationRef} needs. */
function toRecommendationLike(
  recommendation: CampaignRecommendation,
): RecommendationLike {
  return {
    id: recommendation.id,
    title: recommendation.title,
    label: asString(recommendation.label),
    action: recommendation.action,
    type: recommendation.type,
  }
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

  return {
    recommendationRef: deriveRecommendationRef(
      campaignId,
      toRecommendationLike(rec),
      index,
    ),
    title: firstString(rec.title, rec.label, rec.action) ?? 'Recommendation',
    description: firstString(rec.description, rec.reason),
    priority: readPriority(rec.priority),
    confidence: readConfidence(rec.confidence),
    suggestedActionType: suggestActionType(rec),
    source: 'recommendation',
  }
}
