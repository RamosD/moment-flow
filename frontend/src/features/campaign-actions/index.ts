export { buildRecommendationActionDraft } from './recommendation-action-draft'
export type { RecommendationActionDraft } from './recommendation-action-draft'

export {
  DEFAULT_CAMPAIGN_ACTION_PRIORITY,
  MAX_RECOMMENDATION_SNAPSHOT_BYTES,
  buildRecommendationCampaignActionContext,
  buildRecommendationSnapshot,
  normalizeCampaignActionPriority,
} from './recommendation-snapshot'
export type { RecommendationCampaignActionContext } from './recommendation-snapshot'

export { useRecommendationActionDraft } from './useRecommendationActionDraft'

export {
  ACTION_TYPE_OPTIONS,
  ARTIFACT_CAMPAIGN_ACTION_TYPES,
  CAMPAIGN_ACTION_PRIORITY_OPTIONS,
  RECOMMENDATION_CREATE_ACTION_TYPE_OPTIONS,
} from './action-type-options'
export type {
  ArtifactCampaignActionType,
  RecommendationCreateActionType,
} from './action-type-options'

export {
  ACTIVE_CAMPAIGN_ACTION_STATUSES,
  findActiveRecommendationAction,
  groupCampaignActionsByRecommendationRef,
  isActiveCampaignAction,
  matchRecommendationActions,
  recommendationActionDisplayState,
  recommendationExecutionState,
} from './recommendation-action-match'
export type {
  RecommendationActionDisplayState,
  RecommendationExecutionState,
} from './recommendation-action-match'

export { RecommendationActionState } from './RecommendationActionState'
export { RecommendationDecisionActions } from './RecommendationDecisionActions'
export { DismissRecommendationDialog } from './DismissRecommendationDialog'
export { CreateActionFromRecommendationButton } from './CreateActionFromRecommendationButton'
export { CreateActionFromRecommendationDialog } from './CreateActionFromRecommendationDialog'

export {
  CampaignActionPartialSuccessError,
  useCreateActionFromRecommendation,
} from './useCreateActionFromRecommendation'
export type {
  CreateActionFromRecommendationInput,
  CreateActionFromRecommendationMutationInput,
  CreateActionFromRecommendationResult,
  CreatedArtifactReference,
  PartialCampaignActionCreation,
  RetryCampaignActionRegistrationInput,
} from './useCreateActionFromRecommendation'

export { useRecommendationDecision } from './useRecommendationDecision'
export type {
  RecommendationDecisionInput,
  RecommendationDecisionResult,
} from './useRecommendationDecision'
export { buildRecommendationDecisionPayload } from './recommendation-decision-payload'
export type { RecommendationDecisionPayloadInput } from './recommendation-decision-payload'
