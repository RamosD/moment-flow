import type { CampaignAction } from '@/entities/campaign-action'
import {
  campaignActionStatusLabel,
  campaignActionStatusVariant,
  campaignActionTypeLabel,
} from '@/entities/campaign-action'
import { Badge } from '@/shared/ui'

import styles from './campaign-actions.module.css'

/**
 * Compact read-only indicator shown on a recommendation that already has an
 * associated action. Communicates "this recommendation was converted" plus the
 * action's type and current status, so the War Room never re-offers an obvious
 * duplicate.
 */
export function RecommendationActionState({
  action,
}: {
  action: CampaignAction
}) {
  return (
    <span className={styles.state}>
      <Badge variant="info">{campaignActionTypeLabel(action.type)}</Badge>
      <Badge variant={campaignActionStatusVariant(action.status)}>
        {campaignActionStatusLabel(action.status)}
      </Badge>
    </span>
  )
}
