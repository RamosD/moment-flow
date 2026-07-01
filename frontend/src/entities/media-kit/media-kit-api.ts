import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { MediaKit } from './model'

/**
 * List media kits for a campaign (`GET /media-kits/?campaign={id}`).
 * Requires `X-Workspace-ID` (injected). Backend Core only.
 */
export function fetchCampaignMediaKits(
  campaignId: string,
): Promise<PaginatedResponse<MediaKit>> {
  return apiClient.get<PaginatedResponse<MediaKit>>('/media-kits/', {
    params: { campaign: campaignId, page_size: 50 },
  })
}
