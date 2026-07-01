import type { CampaignScores } from '@/entities/campaign'

import { formatScoreValue, humanizeKey, isPrimitive } from './intelligence-format'
import styles from './intelligence.module.css'

/**
 * Renders scores as a read-only grid. Scores are a free-form bag in the
 * contract, so only primitive values are shown (nested data is skipped). The
 * frontend never computes or derives scores.
 */
export function ScoreGrid({ scores }: { scores?: CampaignScores }) {
  const entries = scores
    ? Object.entries(scores).filter(
        (entry): entry is [string, string | number | boolean] =>
          isPrimitive(entry[1]),
      )
    : []

  if (entries.length === 0) return null

  return (
    <div className={styles.scoreGrid}>
      {entries.map(([key, value]) => (
        <div key={key} className={styles.scoreCell}>
          <span className={styles.scoreLabel}>{humanizeKey(key)}</span>
          <span className={styles.scoreValue}>{formatScoreValue(value)}</span>
        </div>
      ))}
    </div>
  )
}
