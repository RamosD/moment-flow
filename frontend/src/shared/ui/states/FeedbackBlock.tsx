import type { ReactNode } from 'react'

import { cx } from '@/shared/lib'

import styles from './states.module.css'

export type FeedbackTone = 'neutral' | 'danger' | 'warning'

export interface FeedbackBlockProps {
  tone?: FeedbackTone
  /** Decorative glyph; a tone-appropriate default is used when omitted. */
  icon?: ReactNode
  title: string
  description?: ReactNode
  /** Action(s), e.g. a retry or sign-in button. */
  actions?: ReactNode
  className?: string
}

const DEFAULT_ICON: Record<FeedbackTone, string> = {
  neutral: '—',
  danger: '!',
  warning: '!',
}

/**
 * Shared presentational block for transversal states (empty / error / dedicated
 * status screens). Danger announces assertively (`role="alert"`); others
 * politely. Never renders tokens or raw error internals — callers pass copy.
 */
export function FeedbackBlock({
  tone = 'neutral',
  icon,
  title,
  description,
  actions,
  className,
}: FeedbackBlockProps) {
  const iconToneClass =
    tone === 'danger'
      ? styles.iconDanger
      : tone === 'warning'
        ? styles.iconWarning
        : undefined

  return (
    <div
      className={cx(styles.block, className)}
      role={tone === 'danger' ? 'alert' : 'status'}
    >
      <span className={cx(styles.icon, iconToneClass)} aria-hidden="true">
        {icon ?? DEFAULT_ICON[tone]}
      </span>
      <span className={styles.title}>{title}</span>
      {description && <p className={styles.description}>{description}</p>}
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  )
}
