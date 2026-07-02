import type { BadgeVariant } from '@/shared/ui'

import type {
  CampaignActionPriority,
  CampaignActionSource,
  CampaignActionStatus,
  CampaignActionType,
  RelatedArtifactStatus,
} from './model'

const STATUS_LABEL: Record<CampaignActionStatus, string> = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Completed',
  failed: 'Failed',
  dismissed: 'Dismissed',
  cancelled: 'Cancelled',
}

export function campaignActionStatusLabel(
  status: CampaignActionStatus,
): string {
  return STATUS_LABEL[status]
}

const STATUS_VARIANT: Record<CampaignActionStatus, BadgeVariant> = {
  pending: 'neutral',
  in_progress: 'warning',
  completed: 'success',
  failed: 'danger',
  dismissed: 'neutral',
  cancelled: 'danger',
}

export function campaignActionStatusVariant(
  status: CampaignActionStatus,
): BadgeVariant {
  return STATUS_VARIANT[status]
}

const TYPE_LABEL: Record<CampaignActionType, string> = {
  content_pack: 'Content pack',
  report_request: 'Report',
  media_kit_request: 'Media kit',
  manual_task: 'Manual task',
  mark_reviewed: 'Mark reviewed',
  dismiss: 'Dismiss',
}

export function campaignActionTypeLabel(type: CampaignActionType): string {
  return TYPE_LABEL[type]
}

const PRIORITY_LABEL: Record<CampaignActionPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  urgent: 'Urgent',
}

export function campaignActionPriorityLabel(
  priority: CampaignActionPriority,
): string {
  return PRIORITY_LABEL[priority]
}

const SOURCE_LABEL: Record<CampaignActionSource, string> = {
  recommendation: 'Recommendation',
  manual: 'Manual',
}

export function campaignActionSourceLabel(source: CampaignActionSource): string {
  return SOURCE_LABEL[source]
}

const ARTIFACT_TYPE_LABEL: Record<RelatedArtifactStatus['type'], string> = {
  report: 'Report',
  media_kit: 'Media kit',
  content_pack_request: 'Content pack',
}

/** The artifact's *own* status (e.g. "Report: failed"), not the action's. */
export function relatedArtifactStatusLabel(artifact: RelatedArtifactStatus): string {
  return `${ARTIFACT_TYPE_LABEL[artifact.type]}: ${artifact.status.replace(/_/g, ' ')}`
}

const ARTIFACT_STATUS_VARIANT: Record<string, BadgeVariant> = {
  completed: 'success',
  generated: 'success',
  published: 'success',
  partially_completed: 'warning',
  processing: 'warning',
  queued: 'neutral',
  draft: 'neutral',
  archived: 'neutral',
  failed: 'danger',
  cancelled: 'danger',
  expired: 'danger',
}

export function relatedArtifactStatusVariant(status: string): BadgeVariant {
  return ARTIFACT_STATUS_VARIANT[status] ?? 'neutral'
}
