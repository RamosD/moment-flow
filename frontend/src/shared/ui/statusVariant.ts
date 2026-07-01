import type { BadgeVariant } from './Badge'

/**
 * Maps a backend status token (content output / report / media kit / campaign)
 * to a Badge color. Unknown/absent statuses stay neutral. Keep the badge text
 * meaningful on its own — color is decorative.
 */
const STATUS_VARIANT: Record<string, BadgeVariant> = {
  // in-progress
  queued: 'neutral',
  validating: 'warning',
  processing: 'warning',
  rendering: 'warning',
  uploading: 'warning',
  // done
  completed: 'success',
  generated: 'success',
  published: 'success',
  active: 'success',
  // failed / terminal-bad
  failed: 'danger',
  cancelled: 'danger',
  expired: 'danger',
  // neutral / lifecycle
  draft: 'neutral',
  scheduled: 'info',
  paused: 'warning',
  archived: 'neutral',
}

export function statusToBadgeVariant(status?: string | null): BadgeVariant {
  if (!status) return 'neutral'
  return STATUS_VARIANT[status] ?? 'neutral'
}
