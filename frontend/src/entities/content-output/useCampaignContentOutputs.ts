import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import { fetchCampaignContentOutputs } from './content-output-api'
import type { ContentOutput } from './model'

export const contentOutputKeys = {
  byCampaign: (workspaceId: string | null, campaignId: string) =>
    ['content-outputs', workspaceId, 'by-campaign', campaignId] as const,
}

/** Content outputs for a campaign. Disabled until workspace + campaign exist. */
export function useCampaignContentOutputs(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  return useQuery<PaginatedResponse<ContentOutput>, unknown, ContentOutput[]>({
    queryKey: contentOutputKeys.byCampaign(workspaceId, campaignId ?? ''),
    queryFn: () => fetchCampaignContentOutputs(campaignId as string),
    enabled: !!workspaceId && !!campaignId,
    select: (data) => data.results,
  })
}
