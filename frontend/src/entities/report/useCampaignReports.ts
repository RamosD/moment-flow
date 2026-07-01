import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import { fetchCampaignReports } from './report-api'
import type { Report } from './model'

export const reportKeys = {
  byCampaign: (workspaceId: string | null, campaignId: string) =>
    ['reports', workspaceId, 'by-campaign', campaignId] as const,
}

/** Reports for a campaign. Disabled until workspace + campaign exist. */
export function useCampaignReports(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  return useQuery<PaginatedResponse<Report>, unknown, Report[]>({
    queryKey: reportKeys.byCampaign(workspaceId, campaignId ?? ''),
    queryFn: () => fetchCampaignReports(campaignId as string),
    enabled: !!workspaceId && !!campaignId,
    select: (data) => data.results,
  })
}
