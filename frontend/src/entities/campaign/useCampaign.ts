import { useQuery } from '@tanstack/react-query'

import { fetchCampaign } from './campaign-api'
import type { Campaign } from './model'
import { campaignKeys } from './query-keys'

/**
 * Retrieve a single campaign. Disabled until both a workspace and a campaign id
 * are available.
 */
export function useCampaign(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  return useQuery<Campaign, unknown, Campaign>({
    queryKey: campaignKeys.detail(workspaceId, campaignId ?? ''),
    queryFn: () => fetchCampaign(campaignId as string),
    enabled: !!workspaceId && !!campaignId,
  })
}
