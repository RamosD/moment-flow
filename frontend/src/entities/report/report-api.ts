import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { CreateReportPayload, Report } from './model'

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

/** Create a report owned by its proprietary domain. */
export function createReport(payload: CreateReportPayload): Promise<Report> {
  return apiClient.post<Report>('/reports/', {
    ...payload,
    report_type: payload.report_type ?? 'campaign_report',
  })
}
