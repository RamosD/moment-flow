import type { TextareaHTMLAttributes } from 'react'

import { cx } from '@/shared/lib'

import styles from './Textarea.module.css'

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>

/** Styled native `<textarea>`. */
export function Textarea({ className, rows = 4, ...rest }: TextareaProps) {
  return (
    <textarea className={cx(styles.textarea, className)} rows={rows} {...rest} />
  )
}
