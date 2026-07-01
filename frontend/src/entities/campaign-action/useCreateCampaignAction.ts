import { useMutation, useQueryClient } from '@tanstack/react-query'

import { createCampaignAction } from './campaign-action-api'
import { invalidateCampaignActionCache } from './invalidate-campaign-action-cache'
import type { CampaignAction, CreateCampaignActionPayload } from './model'

/** Create a persistent CampaignAction and refresh its canonical cache surfaces. */
export function useCreateCampaignAction(workspaceId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<CampaignAction, unknown, CreateCampaignActionPayload>({
    mutationFn: createCampaignAction,
    onSuccess: async (action) => {
      try {
        await invalidateCampaignActionCache(queryClient, workspaceId, action)
      } catch {
        // Never present a completed POST as failed because a refetch failed.
      }
    },
  })
}
