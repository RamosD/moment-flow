import { apiClient } from '@/shared/api'
import type { Workspace } from '@/entities/workspace'
import type { PaginatedResponse } from '@/shared/types'

/**
 * List the workspaces the authenticated user is an active member of.
 * Listing is JWT-scoped and does NOT require `X-Workspace-ID`.
 *
 * `page_size=100` fetches them in one page — a user belongs to a small number
 * of workspaces, so pagination is not needed for the switcher in the MVP.
 */
export function fetchWorkspaces(): Promise<PaginatedResponse<Workspace>> {
  return apiClient.get<PaginatedResponse<Workspace>>('/workspaces/', {
    params: { page_size: 100 },
  })
}
