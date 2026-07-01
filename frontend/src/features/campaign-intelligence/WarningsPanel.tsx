import type { IntelligenceNote } from '@/entities/campaign'
import { Alert } from '@/shared/ui'

import { noteToMessage } from './intelligence-format'
import styles from './intelligence.module.css'

/**
 * Warnings, shown visibly but calmly (a soft "things to keep in mind" notice,
 * not an error). Renders nothing when there are no warnings.
 */
export function WarningsPanel({ warnings }: { warnings?: IntelligenceNote[] }) {
  if (!warnings || warnings.length === 0) return null

  const title =
    warnings.length === 1
      ? '1 thing to keep in mind'
      : `${warnings.length} things to keep in mind`

  return (
    <Alert variant="warning" title={title}>
      <ul className={styles.noteList}>
        {warnings.map((warning, index) => (
          <li key={index}>{noteToMessage(warning)}</li>
        ))}
      </ul>
    </Alert>
  )
}
