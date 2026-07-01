import { Button } from '@/shared/ui'

import { useWorkspace } from './useWorkspace'
import styles from './WorkspaceSwitcher.module.css'

/**
 * Compact workspace selector for the app shell. Renders the right control for
 * each state: a select when ready, inline messages for loading/empty, and a
 * retry on error. Hidden when unauthenticated.
 */
export function WorkspaceSwitcher() {
  const { status, workspaces, activeWorkspace, setWorkspaceId, refetch } =
    useWorkspace()

  if (status === 'unauthenticated') return null

  if (status === 'loading') {
    return <span className={styles.muted}>Loading workspaces…</span>
  }

  if (status === 'error') {
    return (
      <span className={styles.error}>
        Couldn’t load workspaces
        <Button variant="ghost" size="sm" onClick={refetch}>
          Retry
        </Button>
      </span>
    )
  }

  if (status === 'empty') {
    return <span className={styles.muted}>No workspace</span>
  }

  return (
    <div className={styles.switcher}>
      <select
        className={styles.select}
        value={activeWorkspace?.id ?? ''}
        onChange={(e) => setWorkspaceId(e.target.value)}
        aria-label="Active workspace"
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </select>
    </div>
  )
}
