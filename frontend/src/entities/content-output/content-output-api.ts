import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { ContentOutput } from './model'

/**
 * List content outputs for a campaign (`GET /content-outputs/?campaign={id}`).
 * Requires `X-Workspace-ID` (injected). Reads from the Backend Core only — the
 * Content Renderer is never called directly.
 */
export function fetchCampaignContentOutputs(
  campaignId: string,
): Promise<PaginatedResponse<ContentOutput>> {
  return apiClient.get<PaginatedResponse<ContentOutput>>('/content-outputs/', {
    params: { campaign: campaignId, page_size: 50 },
  })
}
