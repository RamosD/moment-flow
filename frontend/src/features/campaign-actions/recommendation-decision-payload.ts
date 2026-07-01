import type {
  CreateDismissCampaignActionPayload,
  CreateMarkReviewedCampaignActionPayload,
} from '@/entities/campaign-action'
import type { UUID } from '@/shared/types'

import type { RecommendationActionDraft } from './recommendation-action-draft'

export type RecommendationDecisionPayloadInput =
  | {
      action_type: 'mark_reviewed'
      campaign: UUID
      draft: RecommendationActionDraft
    }
  | {
      action_type: 'dismiss'
      campaign: UUID
      draft: RecommendationActionDraft
      dismiss_reason: string
    }

/** Build canonical decision POST bodies without status, workspace or metadata. */
export function buildRecommendationDecisionPayload(
  input: RecommendationDecisionPayloadInput,
):
  | CreateMarkReviewedCampaignActionPayload
  | CreateDismissCampaignActionPayload {
  const base = {
    campaign: input.campaign,
    recommendation_ref: input.draft.recommendationRef.ref,
    recommendation_snapshot: input.draft.recommendationSnapshot,
    title: input.draft.title,
    description: input.draft.description ?? '',
    priority: input.draft.priority,
    source: input.draft.source,
  }

  if (input.action_type === 'dismiss') {
    return {
      ...base,
      action_type: 'dismiss',
      dismiss_reason: input.dismiss_reason.trim(),
    }
  }

  return { ...base, action_type: 'mark_reviewed' }
}
