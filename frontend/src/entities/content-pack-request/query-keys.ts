export const contentPackRequestKeys = {
  byCampaign: (workspaceId: string | null, campaignId: string) =>
    ['content-pack-requests', workspaceId, 'by-campaign', campaignId] as const,
}
