import { apiClient } from '@/shared/api'
import type { CampaignIntelligence } from '@/entities/campaign'

/**
 * `POST /api/v1/campaigns/{id}/intelligence/` — synchronous campaign
 * intelligence. The endpoint takes **no request body** and is documented as
 * read-only enrichment (no persistence). The frontend only ever calls the
 * Backend Core here; the Intelligence Engine is never contacted directly.
 */
export function fetchCampaignIntelligence(
  campaignId: string,
): Promise<CampaignIntelligence> {
  return apiClient.post<CampaignIntelligence>(
    `/campaigns/${campaignId}/intelligence/`,
  )
}
