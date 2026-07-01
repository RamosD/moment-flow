import { apiClient } from '@/shared/api'
import type { PaginatedResponse, UUID } from '@/shared/types'

import type {
  CampaignAction,
  CampaignActionSource,
  CampaignActionStatus,
  CampaignActionTransitionPayload,
  CampaignActionType,
  CreateCampaignActionPayload,
  DismissCampaignActionPayload,
  UpdateCampaignActionPayload,
} from './model'
import { sanitizeCampaignActionWritePayload } from './write-payload'

const CAMPAIGN_ACTIONS_PATH = '/campaign-actions/'

export interface CampaignActionFilters {
  campaign?: UUID
  status?: CampaignActionStatus
  action_type?: CampaignActionType
  recommendation_ref?: string
  source?: CampaignActionSource
  created_by?: UUID
}

export interface CampaignActionListParams extends CampaignActionFilters {
  page?: number
  page_size?: number
}

/** GET /campaign-actions/ with exact backend filters and DRF pagination. */
export function fetchCampaignActions(
  params: CampaignActionListParams = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<CampaignAction>> {
  return apiClient.get<PaginatedResponse<CampaignAction>>(
    CAMPAIGN_ACTIONS_PATH,
    {
      params: {
        // Ordering is intentionally omitted: preserve backend default
        // `-created_at` instead of introducing a competing frontend default.
        campaign: params.campaign,
        status: params.status,
        action_type: params.action_type,
        recommendation_ref: params.recommendation_ref,
        source: params.source,
        created_by: params.created_by,
        page: params.page,
        page_size: params.page_size,
      },
      signal,
    },
  )
}

/** Load every page for one exact recommendation + action type lookup. */
export async function fetchAllCampaignActionsByRecommendationType(
  campaign: UUID,
  recommendationRef: string,
  actionType: CampaignActionType,
  signal?: AbortSignal,
): Promise<PaginatedResponse<CampaignAction>> {
  const pageSize = 100
  const params: CampaignActionListParams = {
    campaign,
    recommendation_ref: recommendationRef,
    action_type: actionType,
    page: 1,
    page_size: pageSize,
  }
  const first = await fetchCampaignActions(params, signal)
  const results = [...first.results]
  const pageCount = Math.ceil(first.count / pageSize)

  for (let page = 2; page <= pageCount; page += 1) {
    const nextPage = await fetchCampaignActions(
      { ...params, page },
      signal,
    )
    results.push(...nextPage.results)
  }

  return {
    count: first.count,
    next: null,
    previous: null,
    results,
  }
}

/** GET /campaign-actions/{id}/. */
export function fetchCampaignAction(
  id: UUID,
  signal?: AbortSignal,
): Promise<CampaignAction> {
  return apiClient.get<CampaignAction>(`${CAMPAIGN_ACTIONS_PATH}${id}/`, {
    signal,
  })
}

/** POST /campaign-actions/. */
export function createCampaignAction(
  payload: CreateCampaignActionPayload,
): Promise<CampaignAction> {
  return apiClient.post<CampaignAction>(
    CAMPAIGN_ACTIONS_PATH,
    sanitizeCampaignActionWritePayload(payload),
  )
}

/** PATCH /campaign-actions/{id}/. */
export function updateCampaignAction(
  id: UUID,
  payload: UpdateCampaignActionPayload,
): Promise<CampaignAction> {
  return apiClient.patch<CampaignAction>(
    `${CAMPAIGN_ACTIONS_PATH}${id}/`,
    sanitizeCampaignActionWritePayload(payload),
  )
}

/** POST /campaign-actions/{id}/mark-reviewed/. */
export function markCampaignActionReviewed(id: UUID): Promise<CampaignAction> {
  return apiClient.post<CampaignAction>(
    `${CAMPAIGN_ACTIONS_PATH}${id}/mark-reviewed/`,
  )
}

/** POST /campaign-actions/{id}/dismiss/. */
export function dismissCampaignAction(
  id: UUID,
  payload: DismissCampaignActionPayload,
): Promise<CampaignAction> {
  return apiClient.post<CampaignAction>(
    `${CAMPAIGN_ACTIONS_PATH}${id}/dismiss/`,
    sanitizeCampaignActionWritePayload(payload),
  )
}

/** POST /campaign-actions/{id}/cancel/. */
export function cancelCampaignAction(id: UUID): Promise<CampaignAction> {
  return apiClient.post<CampaignAction>(
    `${CAMPAIGN_ACTIONS_PATH}${id}/cancel/`,
  )
}

/** POST /campaign-actions/{id}/complete/. */
export function completeCampaignAction(id: UUID): Promise<CampaignAction> {
  return apiClient.post<CampaignAction>(
    `${CAMPAIGN_ACTIONS_PATH}${id}/complete/`,
  )
}

/** Dispatch a typed semantic transition to its dedicated endpoint. */
export function transitionCampaignAction(
  id: UUID,
  input: CampaignActionTransitionPayload,
): Promise<CampaignAction> {
  switch (input.transition) {
    case 'mark_reviewed':
      return markCampaignActionReviewed(id)
    case 'dismiss':
      return dismissCampaignAction(id, input.payload)
    case 'cancel':
      return cancelCampaignAction(id)
    case 'complete':
      return completeCampaignAction(id)
  }
}
