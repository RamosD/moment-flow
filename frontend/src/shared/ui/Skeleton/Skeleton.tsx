import { cx } from '@/shared/lib'

import styles from './Skeleton.module.css'

export interface SkeletonProps {
  width?: string | number
  height?: string | number
  radius?: string | number
  className?: string
}

/** Animated placeholder block. Decorative — hidden from assistive tech. */
export function Skeleton({
  width = '100%',
  height = '1rem',
  radius,
  className,
}: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={cx(styles.skeleton, className)}
      style={{ width, height, borderRadius: radius }}
    />
  )
}
