import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import { fetchCampaigns, type CampaignListParams } from './campaign-api'
import type { Campaign } from './model'
import { campaignKeys } from './query-keys'

/**
 * List campaigns for the active workspace. Pass the workspace id explicitly so
 * this entity stays decoupled from the workspace feature; the query is disabled
 * until a workspace is selected.
 */
export function useCampaigns(
  workspaceId: string | null,
  params?: CampaignListParams,
) {
  return useQuery<PaginatedResponse<Campaign>, unknown, Campaign[]>({
    queryKey: campaignKeys.list(workspaceId, params),
    queryFn: () => fetchCampaigns(params),
    enabled: !!workspaceId,
    select: (data) => data.results,
  })
}
