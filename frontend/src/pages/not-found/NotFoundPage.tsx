import styles from './NotFoundPage.module.css'

/**
 * Fallback page for unmatched routes. Wired into the router in FE-004.
 */
export function NotFoundPage() {
  return (
    <div className={styles.wrapper}>
      <p className={styles.code}>404</p>
      <h1>Page not found</h1>
      <p className={styles.message}>
        The page you are looking for does not exist or has moved.
      </p>
    </div>
  )
}
