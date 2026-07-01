import { NavLink, Outlet } from 'react-router-dom'

import { APP_CONFIG } from '@/app/config'
import { useAuth } from '@/features/auth'
import { WorkspaceSwitcher } from '@/features/workspace-switching'
import { Button } from '@/shared/ui'

import styles from './RootLayout.module.css'

/**
 * Application frame: a top bar with primary navigation, the current user and a
 * sign-out action, plus the active route.
 *
 * The richer shell (workspace switcher) moves into widgets/app-shell in later
 * prompts; this stays the minimal frame mounted by the router.
 */
export function RootLayout() {
  const { user, logout } = useAuth()

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <span className={styles.brand}>{APP_CONFIG.name}</span>
        <span className={styles.product}>{APP_CONFIG.productName}</span>
        <nav className={styles.nav}>
          <NavLink to="/" end className={styles.navLink}>
            Dashboard
          </NavLink>
          <NavLink to="/campaigns" className={styles.navLink}>
            Campaigns
          </NavLink>
          <NavLink to="/settings" className={styles.navLink}>
            Settings
          </NavLink>
        </nav>
        <div className={styles.account}>
          <WorkspaceSwitcher />
          {user && (
            <span className={styles.user}>{user.display_name || user.email}</span>
          )}
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
