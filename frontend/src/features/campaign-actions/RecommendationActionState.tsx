import type { CampaignAction } from '@/entities/campaign-action'
import {
  campaignActionTypeLabel,
} from '@/entities/campaign-action'
import type { BadgeVariant } from '@/shared/ui'
import { Badge } from '@/shared/ui'

import { recommendationActionDisplayState } from './recommendation-action-match'
import styles from './campaign-actions.module.css'

const STATE_PRESENTATION = {
  pending: { label: 'Pending', variant: 'neutral' },
  in_progress: { label: 'In progress', variant: 'warning' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'danger' },
  cancelled: { label: 'Cancelled', variant: 'danger' },
  dismissed: { label: 'Dismissed', variant: 'neutral' },
  reviewed: { label: 'Reviewed', variant: 'success' },
} satisfies Record<string, { label: string; variant: BadgeVariant }>

/** Compact state for every persistent action correlated to a recommendation. */
export function RecommendationActionState({
  actions,
  totalCount,
}: {
  actions: CampaignAction[]
  totalCount: number
}) {
  return (
    <span className={styles.state}>
      {actions.map((action) => (
        <span key={action.id} className={styles.stateItem}>
          <Badge variant="info">
            {campaignActionTypeLabel(action.action_type)}
          </Badge>
          <Badge
            variant={
              STATE_PRESENTATION[recommendationActionDisplayState(action)]
                .variant
            }
          >
            {
              STATE_PRESENTATION[recommendationActionDisplayState(action)]
                .label
            }
          </Badge>
        </span>
      ))}
      {totalCount > actions.length && (
        <Badge variant="neutral">+{totalCount - actions.length} more</Badge>
      )}
    </span>
  )
}
