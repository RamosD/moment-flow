import { useQuery } from '@tanstack/react-query'

import type { Workspace } from '@/entities/workspace'

import { fetchWorkspaces } from './workspace-api'

/** Query key for the user's workspaces list. */
export const WORKSPACES_QUERY_KEY = ['workspaces'] as const

/**
 * Loads the user's workspaces. Gated by `enabled` so it only runs once the
 * session is authenticated. Returns the `results` array via `select`.
 */
export function useWorkspaces(enabled: boolean) {
  return useQuery<
    Awaited<ReturnType<typeof fetchWorkspaces>>,
    unknown,
    Workspace[]
  >({
    queryKey: WORKSPACES_QUERY_KEY,
    queryFn: fetchWorkspaces,
    enabled,
    select: (data) => data.results,
    staleTime: 5 * 60_000,
  })
}
