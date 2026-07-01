import { cx } from '@/shared/lib'

import styles from './states.module.css'

export interface LoadingStateProps {
  label?: string
  className?: string
}

/**
 * Centered spinner with an accessible live label. Announces politely so screen
 * readers learn that content is loading.
 */
export function LoadingState({ label = 'Loading…', className }: LoadingStateProps) {
  return (
    <div className={cx(styles.block, className)} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <span className={styles.description}>{label}</span>
    </div>
  )
}
