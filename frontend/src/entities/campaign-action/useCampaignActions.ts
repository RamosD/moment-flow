import { useQuery } from '@tanstack/react-query'

import { fetchCampaignActions } from './campaign-action-api'
import type { CampaignAction } from './model'
import { campaignActionKeys } from './query-keys'

/**
 * Campaign actions for a campaign (aggregated projection over three real
 * Backend Core endpoints). Disabled until workspace + campaign exist.
 */
export function useCampaignActions(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  return useQuery<CampaignAction[]>({
    queryKey: campaignActionKeys.byCampaign(workspaceId, campaignId ?? ''),
    queryFn: () => fetchCampaignActions(campaignId as string),
    enabled: !!workspaceId && !!campaignId,
  })
}
