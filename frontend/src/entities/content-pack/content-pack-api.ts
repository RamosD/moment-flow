import { apiClient } from '@/shared/api'
import type { PaginatedResponse } from '@/shared/types'

import type { ContentPack } from './model'

/**
 * List catalogue content packs (`GET /content-packs/`). Read-only catalogue,
 * workspace-scoped (`X-Workspace-ID` injected). Backend Core only — never the
 * Content Renderer. Defaults to active packs so the picker hides archived rows.
 */
export function fetchContentPacks(): Promise<PaginatedResponse<ContentPack>> {
  return apiClient.get<PaginatedResponse<ContentPack>>('/content-packs/', {
    params: { status: 'active', page_size: 100 },
  })
}
