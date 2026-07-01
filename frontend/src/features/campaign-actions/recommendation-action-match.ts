/**
 * Match a recommendation to an already-created campaign action (CA-009).
 *
 * The Backend Core has NO relational link between a recommendation and the
 * artifact created from it — the only correlation is the frontend-derived
 * `recommendation_ref` written into the artifact `metadata` bag (see
 * `entities/campaign-action/campaign-action-api.ts`). Matching is therefore
 * best-effort: it works for actions this frontend created, and silently finds
 * nothing for artifacts created by other means. This limitation is documented
 * in the phase report — it is not a backend guarantee.
 */

import type { CampaignAction } from '@/entities/campaign-action'

import type { RecommendationActionDraft } from './recommendation-action-draft'

/** Coarse execution state of a recommendation, derived from its matched action. */
export type RecommendationExecutionState =
  | 'not_started'
  | 'action_created'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'

/**
 * Find the action whose stored `recommendation_ref` equals this draft's ref.
 * Returns `null` when none matches (recommendation not yet converted, or its
 * action was created outside this frontend convention).
 */
export function matchRecommendationAction(
  draft: RecommendationActionDraft | null,
  actions: CampaignAction[] | undefined,
): CampaignAction | null {
  if (!draft || !actions || actions.length === 0) return null
  const ref = draft.recommendationRef.ref
  return actions.find((action) => action.recommendationRef === ref) ?? null
}

/** Map a matched action's normalized status to a recommendation execution state. */
export function recommendationExecutionState(
  matched: CampaignAction | null,
): RecommendationExecutionState {
  if (!matched) return 'not_started'
  switch (matched.status) {
    case 'in_progress':
      return 'in_progress'
    case 'completed':
      return 'completed'
    case 'failed':
      return 'failed'
    case 'cancelled':
    case 'dismissed':
      return 'cancelled'
    // pending / unknown → an action exists but hasn't progressed yet.
    default:
      return 'action_created'
  }
}
