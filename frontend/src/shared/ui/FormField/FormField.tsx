import type { ReactNode } from 'react'

import { cx } from '@/shared/lib'

import { InlineFieldError } from '../InlineFieldError'
import styles from './FormField.module.css'

export interface FormFieldProps {
  label: string
  htmlFor: string
  required?: boolean
  hint?: string
  error?: string | null
  children: ReactNode
  className?: string
}

/**
 * Label + control + hint/error grouping for form inputs. Mirrors the
 * label/input pattern already used on the login form, generalized for reuse.
 */
export function FormField({
  label,
  htmlFor,
  required,
  hint,
  error,
  children,
  className,
}: FormFieldProps) {
  return (
    <div className={cx(styles.field, className)}>
      <label className={styles.label} htmlFor={htmlFor}>
        {label}
        {required && (
          <span className={styles.required} aria-hidden="true">
            {' '}
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && <span className={styles.hint}>{hint}</span>}
      <InlineFieldError message={error} />
    </div>
  )
}
