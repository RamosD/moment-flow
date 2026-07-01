/**
 * Label / status / badge helpers for campaign actions.
 *
 * Status normalization maps the three backing artifacts' native enums
 * (content-pack-request / report / media-kit) onto the shared
 * {@link CampaignActionStatus} vocabulary used by badges. The badge-variant
 * mapping returns the same `BadgeVariant` the rest of the UI uses, so callers
 * never reinvent colors. Color is decorative — keep the badge text meaningful.
 */

import type { BadgeVariant } from '@/shared/ui'

import type { CampaignActionStatus, CampaignActionType } from './model'

/** Native artifact status token → normalized status. */
const RAW_STATUS_MAP: Record<string, CampaignActionStatus> = {
  // pre-run
  draft: 'pending',
  queued: 'pending',
  // running
  validating: 'in_progress',
  processing: 'in_progress',
  rendering: 'in_progress',
  uploading: 'in_progress',
  partially_completed: 'in_progress',
  // done
  completed: 'completed',
  generated: 'completed',
  published: 'completed',
  // failed / terminal
  failed: 'failed',
  cancelled: 'cancelled',
  expired: 'cancelled',
  archived: 'cancelled',
}

export function normalizeActionStatus(
  raw?: string | null,
): CampaignActionStatus {
  if (!raw) return 'unknown'
  return RAW_STATUS_MAP[raw] ?? 'unknown'
}

const STATUS_LABEL: Record<CampaignActionStatus, string> = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  dismissed: 'Dismissed',
  unknown: 'Unknown',
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
  cancelled: 'danger',
  dismissed: 'neutral',
  unknown: 'neutral',
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
  asset_request: 'Asset request',
  mark_reviewed: 'Mark reviewed',
  dismiss: 'Dismiss',
}

export function campaignActionTypeLabel(type: CampaignActionType): string {
  return TYPE_LABEL[type]
}
