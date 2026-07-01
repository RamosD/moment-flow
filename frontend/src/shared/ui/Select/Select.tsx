import type { SelectHTMLAttributes } from 'react'

import { cx } from '@/shared/lib'

import styles from './Select.module.css'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  options: SelectOption[]
  placeholder?: string
}

/** Styled native `<select>`. Native semantics keep keyboard/a11y behavior free. */
export function Select({
  options,
  placeholder,
  className,
  ...rest
}: SelectProps) {
  return (
    <select className={cx(styles.select, className)} {...rest}>
      {placeholder && (
        <option value="" disabled hidden>
          {placeholder}
        </option>
      )}
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
