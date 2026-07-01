import type { BadgeVariant } from '@/shared/ui'

import type {
  CampaignActionPriority,
  CampaignActionSource,
  CampaignActionStatus,
  CampaignActionType,
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
