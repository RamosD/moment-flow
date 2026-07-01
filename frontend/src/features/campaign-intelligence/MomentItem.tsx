import type { CampaignMoment } from '@/entities/campaign'
import { Badge } from '@/shared/ui'

import { formatPriority, momentTitle, readString } from './intelligence-format'
import styles from './intelligence.module.css'

/** A single detected moment/signal. Rendered defensively (fields optional). */
export function MomentItem({ moment }: { moment: CampaignMoment }) {
  const priority = formatPriority(moment.priority)
  const description = readString(moment.description)

  return (
    <li className={styles.item}>
      <div className={styles.itemHead}>
        <span className={styles.itemTitle}>{momentTitle(moment)}</span>
        {priority && <Badge variant="info">{priority}</Badge>}
      </div>
      {description && <p className={styles.itemDesc}>{description}</p>}
    </li>
  )
}
