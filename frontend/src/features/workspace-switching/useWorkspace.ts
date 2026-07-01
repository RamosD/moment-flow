import { useContext } from 'react'

import {
  WorkspaceContext,
  type WorkspaceContextValue,
} from './workspace-context'

/** Access the workspace context. Must be used within <WorkspaceProvider>. */
export function useWorkspace(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext)
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider')
  }
  return context
}
