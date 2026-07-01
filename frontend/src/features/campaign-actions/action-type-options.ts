import type {
  CampaignActionPriority,
  CampaignActionType,
} from '@/entities/campaign-action'
import {
  CAMPAIGN_ACTION_PRIORITIES,
  CAMPAIGN_ACTION_TYPES,
  campaignActionPriorityLabel,
  campaignActionTypeLabel,
} from '@/entities/campaign-action'
import type { SelectOption } from '@/shared/ui'

/** Every type persisted by /campaign-actions/. `asset_request` is absent. */
export const ACTION_TYPE_OPTIONS: SelectOption[] = CAMPAIGN_ACTION_TYPES.map(
  (type: CampaignActionType) => ({
    value: type,
    label: campaignActionTypeLabel(type),
  }),
)

export const ARTIFACT_CAMPAIGN_ACTION_TYPES = [
  'content_pack',
  'report_request',
  'media_kit_request',
] as const

export type ArtifactCampaignActionType =
  (typeof ARTIFACT_CAMPAIGN_ACTION_TYPES)[number]

export type RecommendationCreateActionType =
  | ArtifactCampaignActionType
  | 'manual_task'

/**
 * Mark reviewed and dismiss live in their semantic flows. The remaining four
 * types are handled by the recommendation create orchestration.
 */
export const RECOMMENDATION_CREATE_ACTION_TYPE_OPTIONS: SelectOption[] = [
  {
    value: 'manual_task',
    label: campaignActionTypeLabel('manual_task'),
  },
  ...ARTIFACT_CAMPAIGN_ACTION_TYPES.map((type) => ({
    value: type,
    label: campaignActionTypeLabel(type),
  })),
]

export const CAMPAIGN_ACTION_PRIORITY_OPTIONS: SelectOption[] =
  CAMPAIGN_ACTION_PRIORITIES.map((priority: CampaignActionPriority) => ({
    value: priority,
    label: campaignActionPriorityLabel(priority),
  }))
