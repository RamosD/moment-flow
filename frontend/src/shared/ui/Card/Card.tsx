import type { HTMLAttributes } from 'react'

import { cx } from '@/shared/lib'

import styles from './Card.module.css'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'sm' | 'md' | 'lg'
}

/** Neutral surface container. Composition over configuration — pass children. */
export function Card({ padding = 'md', className, ...rest }: CardProps) {
  return <div className={cx(styles.card, styles[padding], className)} {...rest} />
}
