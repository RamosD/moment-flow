import type { InputHTMLAttributes } from 'react'

import { cx } from '@/shared/lib'

import styles from './Input.module.css'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

/** Styled native `<input>`. Defaults `type="text"`; native semantics kept. */
export function Input({ className, type = 'text', ...rest }: InputProps) {
  return <input type={type} className={cx(styles.input, className)} {...rest} />
}
