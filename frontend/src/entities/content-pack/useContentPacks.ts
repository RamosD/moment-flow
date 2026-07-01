import { useQuery } from '@tanstack/react-query'

import type { PaginatedResponse } from '@/shared/types'

import { fetchContentPacks } from './content-pack-api'
import type { ContentPack } from './model'

export const contentPackKeys = {
  all: ['content-packs'] as const,
  catalogue: (workspaceId: string | null) =>
    ['content-packs', workspaceId, 'catalogue'] as const,
}

/**
 * Catalogue content packs for the active workspace. Disabled until a workspace
 * exists and (by default) until explicitly enabled — the picker only needs this
 * when the user actually chooses the content-pack action type.
 */
export function useContentPacks(workspaceId: string | null, enabled = true) {
  return useQuery<PaginatedResponse<ContentPack>, unknown, ContentPack[]>({
    queryKey: contentPackKeys.catalogue(workspaceId),
    queryFn: () => fetchContentPacks(),
    enabled: !!workspaceId && enabled,
    select: (data) => data.results,
  })
}
