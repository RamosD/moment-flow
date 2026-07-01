import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import { fetchCampaignMediaKits } from './media-kit-api'
import type { MediaKit } from './model'

export const mediaKitKeys = {
  byCampaign: (workspaceId: string | null, campaignId: string) =>
    ['media-kits', workspaceId, 'by-campaign', campaignId] as const,
}

/** Media kits for a campaign. Disabled until workspace + campaign exist. */
export function useCampaignMediaKits(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  return useQuery<PaginatedResponse<MediaKit>, unknown, MediaKit[]>({
    queryKey: mediaKitKeys.byCampaign(workspaceId, campaignId ?? ''),
    queryFn: () => fetchCampaignMediaKits(campaignId as string),
    enabled: !!workspaceId && !!campaignId,
    select: (data) => data.results,
  })
}
