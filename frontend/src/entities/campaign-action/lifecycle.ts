import type {
  CampaignAction,
  CampaignActionStatus,
  CampaignActionTransition,
  CreateCampaignActionPayload,
} from './model'

export type PanelCampaignActionTransition = Extract<
  CampaignActionTransition,
  'complete' | 'cancel' | 'dismiss'
>

export const TERMINAL_CAMPAIGN_ACTION_STATUSES = new Set<CampaignActionStatus>([
  'completed',
  'failed',
  'dismissed',
  'cancelled',
])

/** Exact subset of backend transitions exposed by the Campaign Actions Panel. */
export function availablePanelTransitions(
  status: CampaignActionStatus,
): PanelCampaignActionTransition[] {
  if (status === 'pending') return ['complete', 'cancel', 'dismiss']
  if (status === 'in_progress') return ['complete', 'cancel']
  return []
}

/**
 * A failed action is retried as a new record with the same canonical context
 * and formal relations. The failed record is never reopened or overwritten.
 */
export function buildCampaignActionRetryPayload(
  action: CampaignAction,
): CreateCampaignActionPayload | null {
  if (action.status !== 'failed') return null

  const base = {
    campaign: action.campaign,
    title: action.title,
    description: action.description,
    priority: action.priority,
    source: action.source,
    metadata: action.metadata,
  }
  const recommendation = {
    recommendation_ref: action.recommendation_ref,
    recommendation_snapshot: action.recommendation_snapshot,
  }

  switch (action.action_type) {
    case 'content_pack':
      return {
        ...base,
        ...recommendation,
        action_type: 'content_pack',
        related_content_pack_request: action.related_content_pack_request,
        related_content_output: action.related_content_output,
      }
    case 'report_request':
      return {
        ...base,
        ...recommendation,
        action_type: 'report_request',
        related_report: action.related_report,
      }
    case 'media_kit_request':
      return {
        ...base,
        ...recommendation,
        action_type: 'media_kit_request',
        related_media_kit: action.related_media_kit,
      }
    case 'manual_task':
      return {
        ...base,
        action_type: 'manual_task',
        ...(action.recommendation_ref ? recommendation : {}),
      }
    case 'mark_reviewed':
    case 'dismiss':
      return null
  }
}
