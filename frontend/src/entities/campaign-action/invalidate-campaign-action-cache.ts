import type { QueryClient } from '@tanstack/react-query'

import type { CampaignAction } from './model'
import { campaignActionKeys } from './query-keys'

/** Invalidate every canonical cache surface affected by one action mutation. */
export function invalidateCampaignActionCache(
  queryClient: QueryClient,
  workspaceId: string | null,
  action: CampaignAction,
): Promise<unknown[]> {
  const invalidations: Promise<unknown>[] = [
    queryClient.invalidateQueries({
      queryKey: campaignActionKeys.lists(workspaceId, action.campaign),
    }),
    queryClient.invalidateQueries({
      queryKey: campaignActionKeys.detail(workspaceId, action.id),
    }),
  ]

  if (action.recommendation_ref) {
    invalidations.push(
      queryClient.invalidateQueries({
        queryKey: campaignActionKeys.recommendationRoot(
          workspaceId,
          action.campaign,
          action.recommendation_ref,
        ),
      }),
    )
  }

  return Promise.all(invalidations)
}
