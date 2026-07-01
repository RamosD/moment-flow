import type { CampaignMoment } from '@/entities/campaign'

import { MomentItem } from './MomentItem'
import styles from './intelligence.module.css'

/** Detected moments. Honest empty message when none were detected. */
export function MomentsList({ moments }: { moments?: CampaignMoment[] }) {
  if (!moments || moments.length === 0) {
    return <p className={styles.itemDesc}>No moments detected yet.</p>
  }
  return (
    <ul className={styles.list}>
      {moments.map((moment, index) => (
        <MomentItem key={moment.id ?? index} moment={moment} />
      ))}
    </ul>
  )
}
