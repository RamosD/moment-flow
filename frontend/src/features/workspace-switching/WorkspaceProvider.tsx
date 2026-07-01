import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { setWorkspaceProvider } from '@/shared/api'
import { useAuth } from '@/features/auth'

import { useWorkspaces } from './useWorkspaces'
import {
  ACTIVE_WORKSPACE_STORAGE_KEY,
  WorkspaceContext,
  type WorkspaceContextValue,
  type WorkspaceStatus,
} from './workspace-context'

function readStoredWorkspaceId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY)
  } catch {
    return null
  }
}

function persistWorkspaceId(id: string | null): void {
  try {
    if (id) localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, id)
    else localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY)
  } catch {
    // Ignore storage failures; state stays in memory.
  }
}

/**
 * Workspace foundation.
 *
 * Loads the user's workspaces (once authenticated), resolves an active one
 * (persisted preference, falling back to the first when the stored id no longer
 * exists), and exposes its id to the API client as `X-Workspace-ID`. Switching
 * persists the choice and invalidates workspace-scoped queries so all data
 * refetches under the new workspace.
 */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { status: authStatus } = useAuth()
  const isAuthenticated = authStatus === 'authenticated'
  const queryClient = useQueryClient()

  const query = useWorkspaces(isAuthenticated)
  const workspaces = useMemo(() => query.data ?? [], [query.data])

  // Preferred id (user's last choice), seeded from storage.
  const [preferredId, setPreferredId] = useState<string | null>(
    readStoredWorkspaceId,
  )
  // Ref mirrors the *resolved* active id for the API client to read per
  // request.
  const workspaceRef = useRef<string | null>(preferredId)

  useEffect(() => {
    setWorkspaceProvider(() => workspaceRef.current)
  }, [])

  // Resolve the active workspace: prefer the stored choice, else the first.
  const activeWorkspace = useMemo(() => {
    if (workspaces.length === 0) return null
    return workspaces.find((w) => w.id === preferredId) ?? workspaces[0]
  }, [workspaces, preferredId])

  // Sync the ref in a *layout* effect, not a passive one: React runs every
  // layout effect in the tree (parents included) before any passive effect
  // fires, so a consumer further down the tree (e.g. a query whose `enabled`
  // flips true from this same context update, firing its request from a
  // passive effect) always sees the up-to-date id — a passive effect here
  // would race the consumer's own passive effect and could still be stale.
  useLayoutEffect(() => {
    workspaceRef.current = activeWorkspace?.id ?? null
  }, [activeWorkspace])

  // Persisting to storage has no same-commit consumer, so a passive effect
  // is fine.
  useEffect(() => {
    if (isAuthenticated) persistWorkspaceId(activeWorkspace?.id ?? null)
  }, [activeWorkspace, isAuthenticated])

  const setWorkspaceId = useCallback(
    (id: string) => {
      workspaceRef.current = id
      persistWorkspaceId(id)
      setPreferredId(id)
      // Refetch everything scoped to a workspace; keep the workspaces list.
      void queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== 'workspaces',
      })
    },
    [queryClient],
  )

  const status: WorkspaceStatus = !isAuthenticated
    ? 'unauthenticated'
    : query.isError
      ? 'error'
      : query.isPending
        ? 'loading'
        : workspaces.length === 0
          ? 'empty'
          : 'ready'

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      status,
      workspaceId: activeWorkspace?.id ?? null,
      activeWorkspace,
      workspaces,
      setWorkspaceId,
      refetch: () => void query.refetch(),
    }),
    [status, activeWorkspace, workspaces, setWorkspaceId, query],
  )

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  )
}
