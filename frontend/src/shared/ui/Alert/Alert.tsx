import type { ReactNode } from 'react'

import { cx } from '@/shared/lib'

import styles from './Alert.module.css'

export type AlertVariant = 'info' | 'success' | 'warning' | 'danger'

export interface AlertProps {
  variant?: AlertVariant
  title?: string
  children?: ReactNode
  className?: string
}

/**
 * Inline message block. Danger/warning announce assertively (`role="alert"`),
 * info/success politely (`role="status"`), for screen-reader awareness.
 */
export function Alert({
  variant = 'info',
  title,
  children,
  className,
}: AlertProps) {
  const role = variant === 'danger' || variant === 'warning' ? 'alert' : 'status'
  return (
    <div className={cx(styles.alert, styles[variant], className)} role={role}>
      {title && <span className={styles.title}>{title}</span>}
      {children && <div className={styles.body}>{children}</div>}
    </div>
  )
}
