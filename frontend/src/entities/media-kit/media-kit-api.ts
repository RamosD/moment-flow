import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { CreateMediaKitPayload, MediaKit } from './model'

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

/** Create a media kit owned by its proprietary domain. */
export function createMediaKit(
  payload: CreateMediaKitPayload,
): Promise<MediaKit> {
  return apiClient.post<MediaKit>('/media-kits/', payload)
}
