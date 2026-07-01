import type { ReactNode } from 'react'

import { cx } from '@/shared/lib'

import styles from './states.module.css'

export interface EmptyStateProps {
  title: string
  description?: string
  /** Optional call-to-action (e.g. a Button). */
  action?: ReactNode
  /** Optional decorative glyph; defaults to a neutral marker. */
  icon?: ReactNode
  className?: string
}

/** Friendly "nothing here yet" block. */
export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div className={cx(styles.block, className)}>
      <span className={styles.icon} aria-hidden="true">
        {icon ?? '—'}
      </span>
      <span className={styles.title}>{title}</span>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.actions}>{action}</div>}
    </div>
  )
}
