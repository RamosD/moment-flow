import { cx } from '@/shared/lib'

import styles from './InlineFieldError.module.css'

export interface InlineFieldErrorProps {
  message?: string | null
  className?: string
}

/** Small inline validation message. Renders nothing when there is no error. */
export function InlineFieldError({ message, className }: InlineFieldErrorProps) {
  if (!message) return null
  return (
    <span className={cx(styles.error, className)} role="alert">
      {message}
    </span>
  )
}
