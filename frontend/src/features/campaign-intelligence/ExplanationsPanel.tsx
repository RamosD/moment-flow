import type { IntelligenceNote } from '@/entities/campaign'

import { noteToMessage } from './intelligence-format'
import styles from './intelligence.module.css'

/**
 * Explanations, presented as an optional collapsible block — available for the
 * curious without cluttering the main view.
 */
export function ExplanationsPanel({
  explanations,
}: {
  explanations?: IntelligenceNote[]
}) {
  if (!explanations || explanations.length === 0) return null

  return (
    <details className={styles.explanations}>
      <summary className={styles.explanationsSummary}>
        Why these results? ({explanations.length})
      </summary>
      <div className={styles.explanationsBody}>
        <ul className={styles.noteList}>
          {explanations.map((explanation, index) => (
            <li key={index}>{noteToMessage(explanation)}</li>
          ))}
        </ul>
      </div>
    </details>
  )
}
