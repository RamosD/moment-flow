import type { ButtonHTMLAttributes } from 'react'

import { cx } from '@/shared/lib'

import styles from './Button.module.css'

export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'ghost'
  | 'danger'
  | 'success'
  | 'warning'
  | 'neutral'

export type ButtonSize = 'sm' | 'md'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  fullWidth?: boolean
}

/**
 * Base button. Defaults `type="button"` so it never accidentally submits a
 * form; pass `type="submit"` explicitly when needed. Native `disabled` is
 * respected for both behaviour and styling.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  type,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type ?? 'button'}
      className={cx(
        styles.button,
        styles[variant],
        styles[size],
        fullWidth && styles.fullWidth,
        className,
      )}
      {...rest}
    />
  )
}
