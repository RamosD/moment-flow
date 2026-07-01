import { useMemo } from 'react'

import type { CampaignRecommendation } from '@/entities/campaign'

import {
  buildRecommendationActionDraft,
  type RecommendationActionDraft,
} from './recommendation-action-draft'

/**
 * Memoized draft builder for a single recommendation. Returns `null` until a
 * campaign id is known — a draft without a campaign cannot be turned into an
 * action (every supported endpoint is campaign-scoped).
 */
export function useRecommendationActionDraft(
  campaignId: string | undefined,
  recommendation: CampaignRecommendation | undefined,
  index: number,
): RecommendationActionDraft | null {
  return useMemo(() => {
    if (!campaignId) return null
    return buildRecommendationActionDraft(campaignId, recommendation, index)
  }, [campaignId, recommendation, index])
}
