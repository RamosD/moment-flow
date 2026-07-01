import { useQuery } from '@tanstack/react-query'

import { fetchCampaignAction } from './campaign-action-api'
import type { CampaignAction } from './model'
import { campaignActionKeys } from './query-keys'

/** Retrieve one persistent CampaignAction by its own id. */
export function useCampaignAction(
  workspaceId: string | null,
  actionId: string | undefined,
) {
  return useQuery<CampaignAction>({
    queryKey: campaignActionKeys.detail(workspaceId, actionId ?? ''),
    queryFn: ({ signal }) => fetchCampaignAction(actionId as string, signal),
    enabled: !!workspaceId && !!actionId,
  })
}
