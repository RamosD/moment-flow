import type { ISODateTimeString, Metadata, UUID } from '@/shared/types'

/** Exact action_type values exposed by the persistent CampaignAction API. */
export const CAMPAIGN_ACTION_TYPES = [
  'content_pack',
  'report_request',
  'media_kit_request',
  'manual_task',
  'mark_reviewed',
  'dismiss',
] as const

export type CampaignActionType = (typeof CAMPAIGN_ACTION_TYPES)[number]

/** `asset_request` is deliberately absent: it is not a backend action type. */
export const CAMPAIGN_ACTION_STATUSES = [
  'pending',
  'in_progress',
  'completed',
  'failed',
  'dismissed',
  'cancelled',
] as const

export type CampaignActionStatus = (typeof CAMPAIGN_ACTION_STATUSES)[number]

export const CAMPAIGN_ACTION_PRIORITIES = [
  'low',
  'medium',
  'high',
  'urgent',
] as const

export type CampaignActionPriority =
  (typeof CAMPAIGN_ACTION_PRIORITIES)[number]

export const CAMPAIGN_ACTION_SOURCES = ['recommendation', 'manual'] as const

export type CampaignActionSource = (typeof CAMPAIGN_ACTION_SOURCES)[number]

/**
 * Persistent CampaignAction representation returned by the Backend Core.
 *
 * Entities in this frontend mirror API field names, so the canonical model is
 * intentionally snake_case and needs no DTO-to-model mapper.
 */
export interface CampaignAction {
  id: UUID
  workspace: UUID
  campaign: UUID
  recommendation_ref: string
  recommendation_snapshot: Metadata
  title: string
  description: string
  action_type: CampaignActionType
  status: CampaignActionStatus
  priority: CampaignActionPriority
  source: CampaignActionSource
  dismiss_reason: string
  metadata: Metadata
  related_content_pack_request: UUID | null
  related_content_output: UUID | null
  related_report: UUID | null
  related_media_kit: UUID | null
  created_by: UUID | null
  completed_at: ISODateTimeString | null
  cancelled_at: ISODateTimeString | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
}

interface CreateCampaignActionBasePayload {
  campaign: UUID
  title: string
  description?: string
  status?: CampaignActionStatus
  priority?: CampaignActionPriority
  source?: CampaignActionSource
  dismiss_reason?: string
  metadata?: Metadata
}

interface RecommendationCampaignActionFields {
  recommendation_ref: string
  recommendation_snapshot: Metadata
}

interface NoRelatedArtifactFields {
  related_content_pack_request?: never
  related_content_output?: never
  related_report?: never
  related_media_kit?: never
}

export interface CreateContentPackCampaignActionPayload
  extends CreateCampaignActionBasePayload,
    RecommendationCampaignActionFields {
  action_type: 'content_pack'
  related_content_pack_request?: UUID | null
  related_content_output?: UUID | null
  related_report?: never
  related_media_kit?: never
}

export interface CreateReportCampaignActionPayload
  extends CreateCampaignActionBasePayload,
    RecommendationCampaignActionFields {
  action_type: 'report_request'
  related_content_pack_request?: never
  related_content_output?: never
  related_report?: UUID | null
  related_media_kit?: never
}

export interface CreateMediaKitCampaignActionPayload
  extends CreateCampaignActionBasePayload,
    RecommendationCampaignActionFields {
  action_type: 'media_kit_request'
  related_content_pack_request?: never
  related_content_output?: never
  related_report?: never
  related_media_kit?: UUID | null
}

export interface CreateManualTaskCampaignActionPayload
  extends CreateCampaignActionBasePayload,
    NoRelatedArtifactFields {
  action_type: 'manual_task'
  recommendation_ref?: string
  recommendation_snapshot?: Metadata
}

export interface CreateMarkReviewedCampaignActionPayload
  extends CreateCampaignActionBasePayload,
    RecommendationCampaignActionFields,
    NoRelatedArtifactFields {
  action_type: 'mark_reviewed'
  status?: 'completed'
}

export interface CreateDismissCampaignActionPayload
  extends CreateCampaignActionBasePayload,
    RecommendationCampaignActionFields,
    NoRelatedArtifactFields {
  action_type: 'dismiss'
  status?: 'dismissed'
  dismiss_reason: string
}

/** Writable fields accepted by POST /campaign-actions/. */
export type CreateCampaignActionPayload =
  | CreateContentPackCampaignActionPayload
  | CreateReportCampaignActionPayload
  | CreateMediaKitCampaignActionPayload
  | CreateManualTaskCampaignActionPayload
  | CreateMarkReviewedCampaignActionPayload
  | CreateDismissCampaignActionPayload

/**
 * Writable fields accepted by PATCH /campaign-actions/{id}/.
 * Immutable and server-managed fields are intentionally impossible to send.
 */
export interface UpdateCampaignActionPayload {
  title?: string
  description?: string
  status?: CampaignActionStatus
  priority?: CampaignActionPriority
  dismiss_reason?: string
  metadata?: Metadata
  related_content_pack_request?: UUID | null
  related_content_output?: UUID | null
  related_report?: UUID | null
  related_media_kit?: UUID | null
}

/** Body accepted by POST /campaign-actions/{id}/dismiss/. */
export interface DismissCampaignActionPayload {
  dismiss_reason: string
}

export type CampaignActionTransition =
  | 'mark_reviewed'
  | 'dismiss'
  | 'cancel'
  | 'complete'

/** Input for semantic transition endpoints. Only dismiss accepts a body. */
export type CampaignActionTransitionPayload =
  | {
      transition: Exclude<CampaignActionTransition, 'dismiss'>
      payload?: never
    }
  | {
      transition: 'dismiss'
      payload: DismissCampaignActionPayload
    }

export type CampaignActionTransitionInput = CampaignActionTransitionPayload & {
  id: UUID
}
