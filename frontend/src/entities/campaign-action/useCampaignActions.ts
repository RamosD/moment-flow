import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import {
  fetchCampaignActions,
  type CampaignActionListParams,
} from './campaign-action-api'
import type { CampaignAction } from './model'
import { campaignActionListKey } from './query-keys'

export type UseCampaignActionsParams = Omit<
  CampaignActionListParams,
  'campaign'
>

/** Paginated CampaignActions for one campaign, with exact backend filters. */
export function useCampaignActions(
  workspaceId: string | null,
  campaignId: string | undefined,
  params: UseCampaignActionsParams = {},
) {
  const requestParams: CampaignActionListParams = {
    ...params,
    campaign: campaignId,
  }

  return useQuery<PaginatedResponse<CampaignAction>>({
    queryKey: campaignActionListKey(
      workspaceId,
      campaignId ?? '',
      requestParams,
    ),
    queryFn: ({ signal }) => fetchCampaignActions(requestParams, signal),
    enabled: !!workspaceId && !!campaignId,
  })
}
