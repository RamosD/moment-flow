import type { CampaignActionListParams } from './campaign-action-api'

function normalizedParams(params: CampaignActionListParams) {
  return {
    status: params.status,
    action_type: params.action_type,
    recommendation_ref: params.recommendation_ref,
    source: params.source,
    created_by: params.created_by,
    page: params.page,
    page_size: params.page_size,
  }
}

/** Workspace, campaign, filters and pagination are part of every list key. */
export const campaignActionKeys = {
  all: ['campaign-actions'] as const,
  workspace: (workspaceId: string | null) =>
    ['campaign-actions', workspaceId] as const,
  lists: (workspaceId: string | null, campaignId: string) =>
    ['campaign-actions', workspaceId, 'campaign', campaignId, 'list'] as const,
  list: (
    workspaceId: string | null,
    campaignId: string,
    params: CampaignActionListParams = {},
  ) =>
    [
      'campaign-actions',
      workspaceId,
      'campaign',
      campaignId,
      'list',
      normalizedParams(params),
    ] as const,
  recommendations: (workspaceId: string | null, campaignId: string) =>
    [
      'campaign-actions',
      workspaceId,
      'campaign',
      campaignId,
      'recommendation',
    ] as const,
  recommendationRoot: (
    workspaceId: string | null,
    campaignId: string,
    recommendationRef: string,
  ) =>
    [
      'campaign-actions',
      workspaceId,
      'campaign',
      campaignId,
      'recommendation',
      recommendationRef,
    ] as const,
  recommendation: (
    workspaceId: string | null,
    campaignId: string,
    recommendationRef: string,
    params: CampaignActionListParams = {},
  ) =>
    [
      ...campaignActionKeys.recommendationRoot(
        workspaceId,
        campaignId,
        recommendationRef,
      ),
      normalizedParams(params),
    ] as const,
  details: (workspaceId: string | null) =>
    ['campaign-actions', workspaceId, 'detail'] as const,
  detail: (workspaceId: string | null, id: string) =>
    ['campaign-actions', workspaceId, 'detail', id] as const,
}

export function campaignActionListKey(
  workspaceId: string | null,
  campaignId: string,
  params: CampaignActionListParams,
) {
  return params.recommendation_ref
    ? campaignActionKeys.recommendation(
        workspaceId,
        campaignId,
        params.recommendation_ref,
        params,
      )
    : campaignActionKeys.list(workspaceId, campaignId, params)
}
