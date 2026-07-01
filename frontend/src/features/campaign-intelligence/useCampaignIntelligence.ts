import { useQuery } from '@tanstack/react-query'

import type { CampaignIntelligence } from '@/entities/campaign'

import { fetchCampaignIntelligence } from './intelligence-api'

/** Query key for campaign intelligence: scoped by workspace + campaign. */
export const intelligenceKeys = {
  detail: (workspaceId: string | null, campaignId: string) =>
    ['campaign-intelligence', workspaceId, campaignId] as const,
}

/**
 * Loads a campaign's intelligence.
 *
 * Technical decision: although the endpoint is an HTTP **POST**, it is
 * semantically a **read** (read-only enrichment, no persistence, no body). We
 * therefore expose it with `useQuery` — the War Room wants it fetched on mount,
 * cached, retried on transient 5xx, and refreshable — rather than a mutation.
 * A longer `staleTime` avoids re-triggering the engine on every navigation.
 */
export function useCampaignIntelligence(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  return useQuery<CampaignIntelligence, unknown, CampaignIntelligence>({
    queryKey: intelligenceKeys.detail(workspaceId, campaignId ?? ''),
    queryFn: () => fetchCampaignIntelligence(campaignId as string),
    enabled: !!workspaceId && !!campaignId,
    staleTime: 2 * 60_000,
    gcTime: 5 * 60_000,
  })
}
