import type { ReactNode } from 'react'

import { cx } from '@/shared/lib'

import styles from './Section.module.css'

export interface SectionProps {
  title?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

/** Titled content block used to group related panels within a page. */
export function Section({
  title,
  description,
  actions,
  children,
  className,
}: SectionProps) {
  return (
    <section className={cx(styles.section, className)}>
      {(title || actions) && (
        <div className={styles.head}>
          <div className={styles.titles}>
            {title && <h2>{title}</h2>}
            {description && <p className={styles.description}>{description}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  )
}
