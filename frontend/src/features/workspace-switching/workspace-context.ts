import { createContext } from 'react'

import type { Workspace } from '@/entities/workspace'

export type WorkspaceStatus =
  | 'unauthenticated'
  | 'loading'
  | 'error'
  | 'empty'
  | 'ready'

export interface WorkspaceContextValue {
  /**
   * - `unauthenticated`: no session, nothing loaded.
   * - `loading`: fetching the user's workspaces.
   * - `error`: the workspaces request failed.
   * - `empty`: the user belongs to no workspace.
   * - `ready`: an active workspace is available.
   */
  status: WorkspaceStatus
  /** Active workspace id (also injected as `X-Workspace-ID`), or null. */
  workspaceId: string | null
  /** The resolved active workspace object, or null. */
  activeWorkspace: Workspace | null
  /** All workspaces the user can access. */
  workspaces: Workspace[]
  /** Select the active workspace. Persists it and invalidates scoped queries. */
  setWorkspaceId: (id: string) => void
  /** Retry loading the workspaces. */
  refetch: () => void
}

export const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(
  undefined,
)

/** localStorage key for the active workspace id. */
export const ACTIVE_WORKSPACE_STORAGE_KEY = 'mf.active_workspace_id'
