import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { Campaign, CampaignStatus } from './model'

export interface CampaignListParams {
  search?: string
  status?: CampaignStatus
  ordering?: string
  page?: number
  page_size?: number
}

/**
 * List campaigns in the active workspace.
 * Requires `X-Workspace-ID` (injected automatically by the workspace provider).
 */
export function fetchCampaigns(
  params: CampaignListParams = {},
): Promise<PaginatedResponse<Campaign>> {
  return apiClient.get<PaginatedResponse<Campaign>>('/campaigns/', {
    // Object literal (not the named type) so it satisfies the params index
    // signature; undefined values are skipped by the client.
    params: {
      search: params.search,
      status: params.status,
      ordering: params.ordering,
      page: params.page,
      page_size: params.page_size,
    },
  })
}

/** Retrieve a single campaign by id, in the active workspace. */
export function fetchCampaign(id: string): Promise<Campaign> {
  return apiClient.get<Campaign>(`/campaigns/${id}/`)
}
