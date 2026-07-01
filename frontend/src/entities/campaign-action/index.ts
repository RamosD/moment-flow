export type * from './model'
export {
  CAMPAIGN_ACTION_TYPES,
  CAMPAIGN_ACTION_STATUSES,
  CAMPAIGN_ACTION_PRIORITIES,
  CAMPAIGN_ACTION_SOURCES,
} from './model'

export type { RecommendationLike, RecommendationRef } from './recommendation-ref'
export {
  MAX_RECOMMENDATION_REF_LENGTH,
  deriveRecommendationRef,
  normalizeRecommendationRef,
} from './recommendation-ref'

export {
  campaignActionStatusLabel,
  campaignActionStatusVariant,
  campaignActionTypeLabel,
  campaignActionPriorityLabel,
  campaignActionSourceLabel,
} from './helpers'

export { campaignActionKeys } from './query-keys'

export type {
  CampaignActionFilters,
  CampaignActionListParams,
} from './campaign-action-api'
export {
  fetchCampaignActions,
  fetchAllCampaignActionsByRecommendationType,
  fetchCampaignAction,
  createCampaignAction,
  updateCampaignAction,
  markCampaignActionReviewed,
  dismissCampaignAction,
  cancelCampaignAction,
  completeCampaignAction,
  transitionCampaignAction,
} from './campaign-action-api'
export { sanitizeCampaignActionWritePayload } from './write-payload'

export type { UseCampaignActionsParams } from './useCampaignActions'
export { useCampaignActions } from './useCampaignActions'
export {
  RECOMMENDATION_ACTION_PAGE_SIZE,
  useAllCampaignActionsByRecommendationType,
  useCampaignActionsByRecommendation,
} from './useCampaignActionsByRecommendation'
export { useCampaignAction } from './useCampaignAction'
export { useCreateCampaignAction } from './useCreateCampaignAction'
export type { UpdateCampaignActionInput } from './useUpdateCampaignAction'
export { useUpdateCampaignAction } from './useUpdateCampaignAction'
export { useCampaignActionTransition } from './useCampaignActionTransition'
export { invalidateCampaignActionCache } from './invalidate-campaign-action-cache'
export {
  TERMINAL_CAMPAIGN_ACTION_STATUSES,
  availablePanelTransitions,
  buildCampaignActionRetryPayload,
} from './lifecycle'
export type { PanelCampaignActionTransition } from './lifecycle'
