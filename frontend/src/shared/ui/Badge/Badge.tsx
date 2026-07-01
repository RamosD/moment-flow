import type { HTMLAttributes } from 'react'

import { cx } from '@/shared/lib'

import styles from './Badge.module.css'

export type BadgeVariant =
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

/** Small status label. Color is decorative — keep the text meaningful on its own. */
export function Badge({ variant = 'neutral', className, ...rest }: BadgeProps) {
  return (
    <span className={cx(styles.badge, styles[variant], className)} {...rest} />
  )
}
