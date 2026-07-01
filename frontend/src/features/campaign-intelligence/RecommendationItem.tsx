import type { ReactNode } from 'react'

import type { CampaignRecommendation } from '@/entities/campaign'
import { Badge } from '@/shared/ui'

import {
  formatPriority,
  readString,
  recommendationTitle,
} from './intelligence-format'
import styles from './intelligence.module.css'

/**
 * A single recommendation. Display-only by default; an optional `action` slot
 * lets a higher layer (the War Room page, via the campaign-actions feature)
 * attach an execution affordance without this feature depending on it — the
 * intelligence feature stays decoupled from campaign-actions.
 */
export function RecommendationItem({
  recommendation,
  action,
}: {
  recommendation: CampaignRecommendation
  action?: ReactNode
}) {
  const priority = formatPriority(recommendation.priority)
  const description =
    readString(recommendation.description) ?? readString(recommendation.action)

  return (
    <li className={styles.item}>
      <div className={styles.itemHead}>
        <span className={styles.itemTitle}>
          {recommendationTitle(recommendation)}
        </span>
        {priority && <Badge variant="primary">{priority}</Badge>}
      </div>
      {description && <p className={styles.itemDesc}>{description}</p>}
      {action && <div className={styles.itemAction}>{action}</div>}
    </li>
  )
}
