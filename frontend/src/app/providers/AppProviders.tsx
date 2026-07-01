import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '@/features/auth'
import { WorkspaceProvider } from '@/features/workspace-switching'

import { queryClient } from './queryClient'

/**
 * Global application providers, composed in one place.
 *
 * Order: QueryClient (server state) → Auth (token) → Workspace (X-Workspace-ID).
 * Auth/Workspace register their getters with the API client on mount, so any
 * query/mutation issued by children automatically carries the right headers.
 */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WorkspaceProvider>{children}</WorkspaceProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
