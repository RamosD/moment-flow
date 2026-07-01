import type {
  CampaignAction,
  CampaignActionStatus,
  CampaignActionType,
} from '@/entities/campaign-action'

import type { RecommendationActionDraft } from './recommendation-action-draft'

export type RecommendationExecutionState =
  | 'not_started'
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'dismissed'
  | 'cancelled'
  | 'reviewed'

export type RecommendationActionDisplayState = Exclude<
  RecommendationExecutionState,
  'not_started'
>

export const ACTIVE_CAMPAIGN_ACTION_STATUSES = new Set<CampaignActionStatus>([
  'pending',
  'in_progress',
  'completed',
])

/** Group persistent actions by their canonical top-level recommendation ref. */
export function groupCampaignActionsByRecommendationRef(
  actions: CampaignAction[] | undefined,
): Map<string, CampaignAction[]> {
  const grouped = new Map<string, CampaignAction[]>()

  for (const action of actions ?? []) {
    const current = grouped.get(action.recommendation_ref)
    if (current) current.push(action)
    else grouped.set(action.recommendation_ref, [action])
  }

  return grouped
}

/** Return every persistent action with the recommendation's exact top-level ref. */
export function matchRecommendationActions(
  draft: RecommendationActionDraft | null,
  actions: CampaignAction[] | undefined,
): CampaignAction[] {
  if (!draft) return []
  return (
    groupCampaignActionsByRecommendationRef(actions).get(
      draft.recommendationRef.ref,
    ) ?? []
  )
}

export function isActiveCampaignAction(action: CampaignAction): boolean {
  return ACTIVE_CAMPAIGN_ACTION_STATUSES.has(action.status)
}

/** The backend permits at most one active action for the same ref + type. */
export function findActiveRecommendationAction(
  actions: CampaignAction[],
  actionType: CampaignActionType,
): CampaignAction | undefined {
  return actions.find(
    (action) =>
      action.action_type === actionType && isActiveCampaignAction(action),
  )
}

/** Translate the persisted lifecycle into the recommendation-facing state. */
export function recommendationActionDisplayState(
  action: CampaignAction,
): RecommendationActionDisplayState {
  if (
    action.action_type === 'mark_reviewed' &&
    action.status === 'completed'
  ) {
    return 'reviewed'
  }
  return action.status
}

/** Coarse aggregate state retained for callers that need a single summary. */
export function recommendationExecutionState(
  actions: CampaignAction[],
): RecommendationExecutionState {
  if (actions.length === 0) return 'not_started'
  if (actions.some((action) => action.status === 'in_progress')) {
    return 'in_progress'
  }
  if (actions.some((action) => action.status === 'pending')) {
    return 'pending'
  }
  if (
    actions.some(
      (action) =>
        recommendationActionDisplayState(action) === 'reviewed',
    )
  ) {
    return 'reviewed'
  }
  if (actions.some((action) => action.status === 'completed')) {
    return 'completed'
  }
  if (actions.some((action) => action.status === 'failed')) return 'failed'
  if (actions.some((action) => action.status === 'dismissed')) return 'dismissed'
  return 'cancelled'
}
