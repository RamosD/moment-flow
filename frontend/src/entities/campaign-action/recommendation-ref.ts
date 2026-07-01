/**
 * Defensive recommendation references.
 *
 * Recommendations come from the Intelligence Engine via the Backend Core and
 * are NOT persisted (`POST /campaigns/{id}/intelligence/` is recomputed every
 * call) and frequently lack a stable `id`. To correlate a recommendation with
 * an action without inventing a backend contract, we derive a stable key from
 * `campaignId + index + title/action/type`. Treat it strictly as a frontend
 * correlation hint — never as a Backend Core persistent identifier.
 */

import type { UUID } from '@/shared/types'

/**
 * Minimal structural shape of a recommendation. Declared locally (rather than
 * importing the campaign entity's `CampaignRecommendation`) to keep entities
 * decoupled — entities import from `shared` only.
 */
export interface RecommendationLike {
  id?: string | number
  title?: string
  label?: string
  action?: string
  type?: string
  [key: string]: unknown
}

export interface RecommendationRef {
  /** Stable correlation key. Defensive — not a backend identifier. */
  ref: string
  campaignId: UUID
  index: number
  /** The recommendation's own id when present, else `null`. */
  recommendationId: string | null
  title: string | null
  action: string | null
  type: string | null
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return null
}

/**
 * Derive a stable, defensive reference for an intelligence recommendation.
 * Prefers the recommendation's own `id` when present; otherwise falls back to a
 * positional + content-derived key so list re-renders stay stable even when the
 * engine omits ids.
 */
export function deriveRecommendationRef(
  campaignId: UUID,
  recommendation: RecommendationLike | undefined,
  index: number,
): RecommendationRef {
  const rec = recommendation ?? {}
  const recommendationId = rec.id != null ? String(rec.id) : null
  const title = firstString(rec.title, rec.label)
  const action = firstString(rec.action)
  const type = firstString(rec.type)

  const ref = recommendationId
    ? `${campaignId}:id:${recommendationId}`
    : `${campaignId}:i${index}:${slugify(title ?? action ?? type ?? 'rec') || 'rec'}`

  return { ref, campaignId, index, recommendationId, title, action, type }
}
