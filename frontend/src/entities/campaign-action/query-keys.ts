/**
 * Query keys for campaign actions. Scoped by workspace + campaign so cache
 * entries never leak across workspaces. The aggregate list reads three real
 * endpoints (content-pack-requests / reports / media-kits) behind one key.
 */

export const campaignActionKeys = {
  all: ['campaign-actions'] as const,
  byCampaign: (workspaceId: string | null, campaignId: string) =>
    ['campaign-actions', workspaceId, 'by-campaign', campaignId] as const,
}
