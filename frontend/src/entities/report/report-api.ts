import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { Report } from './model'

/**
 * List reports for a campaign (`GET /reports/?campaign={id}`).
 * Requires `X-Workspace-ID` (injected). Backend Core only.
 */
export function fetchCampaignReports(
  campaignId: string,
): Promise<PaginatedResponse<Report>> {
  return apiClient.get<PaginatedResponse<Report>>('/reports/', {
    params: { campaign: campaignId, page_size: 50 },
  })
}
