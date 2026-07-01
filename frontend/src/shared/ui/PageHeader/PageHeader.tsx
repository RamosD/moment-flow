import type { ReactNode } from 'react'

import styles from './PageHeader.module.css'

export interface PageHeaderProps {
  title: string
  description?: string
  /** Optional right-aligned actions (e.g. primary button). */
  actions?: ReactNode
}

/** Page-level heading with optional description and action slot. */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.titles}>
        <h1>{title}</h1>
        {description && <p className={styles.description}>{description}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  )
}
