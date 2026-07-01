import { useMutation, useQueryClient } from '@tanstack/react-query'

import { transitionCampaignAction } from './campaign-action-api'
import { invalidateCampaignActionCache } from './invalidate-campaign-action-cache'
import type {
  CampaignAction,
  CampaignActionTransitionInput,
} from './model'

/** Execute mark-reviewed, dismiss, cancel or complete on an existing action. */
export function useCampaignActionTransition(workspaceId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<CampaignAction, unknown, CampaignActionTransitionInput>({
    mutationFn: ({ id, ...transition }) =>
      transitionCampaignAction(id, transition),
    onSuccess: async (action) => {
      try {
        await invalidateCampaignActionCache(queryClient, workspaceId, action)
      } catch {
        // A failed refetch does not undo the completed backend transition.
      }
    },
  })
}
