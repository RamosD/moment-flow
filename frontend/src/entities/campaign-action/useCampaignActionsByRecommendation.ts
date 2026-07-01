import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import { fetchAllCampaignActionsByRecommendationType } from './campaign-action-api'
import { useCampaignActions } from './useCampaignActions'
import type { CampaignAction, CampaignActionType } from './model'
import { campaignActionKeys } from './query-keys'

/** Backend maximum; enough for existence checks without claiming completeness. */
export const RECOMMENDATION_ACTION_PAGE_SIZE = 100

/**
 * Exact CampaignAction lookup for one recommendation within one campaign.
 *
 * Consumers must use the response `count` to decide existence. `results` is a
 * page and may be incomplete when count exceeds the backend page-size maximum.
 */
export function useCampaignActionsByRecommendation(
  workspaceId: string | null,
  campaignId: string | undefined,
  recommendationRef: string | undefined,
  actionType?: CampaignActionType,
) {
  return useCampaignActions(
    workspaceId,
    recommendationRef ? campaignId : undefined,
    {
      recommendation_ref: recommendationRef,
      action_type: actionType,
      page: 1,
      page_size: RECOMMENDATION_ACTION_PAGE_SIZE,
    },
  )
}

/**
 * Load every page for one exact recommendation + action type.
 *
 * This query is reserved for duplicate checks while the create dialog is open;
 * the lighter recommendation summary query remains a single explicit page.
 */
export function useAllCampaignActionsByRecommendationType(
  workspaceId: string | null,
  campaignId: string | undefined,
  recommendationRef: string | undefined,
  actionType: CampaignActionType,
) {
  const params = {
    campaign: campaignId,
    recommendation_ref: recommendationRef,
    action_type: actionType,
    page: 1,
    page_size: RECOMMENDATION_ACTION_PAGE_SIZE,
  }

  return useQuery<PaginatedResponse<CampaignAction>>({
    queryKey: [
      ...campaignActionKeys.recommendation(
        workspaceId,
        campaignId ?? '',
        recommendationRef ?? '',
        params,
      ),
      'all-pages',
    ],
    queryFn: ({ signal }) =>
      fetchAllCampaignActionsByRecommendationType(
        campaignId!,
        recommendationRef!,
        actionType,
        signal,
      ),
    enabled: !!workspaceId && !!campaignId && !!recommendationRef,
  })
}
