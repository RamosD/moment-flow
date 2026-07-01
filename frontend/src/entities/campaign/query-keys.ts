import type { CampaignListParams } from './campaign-api'

/**
 * Query keys for campaign data. The active `workspaceId` is part of every key so
 * each workspace gets its own cache entry (and switching invalidates the rest).
 */
export const campaignKeys = {
  list: (workspaceId: string | null, params?: CampaignListParams) =>
    ['campaigns', workspaceId, 'list', params ?? {}] as const,
  detail: (workspaceId: string | null, id: string) =>
    ['campaigns', workspaceId, 'detail', id] as const,
}
