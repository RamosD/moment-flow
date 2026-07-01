import { useMutation, useQueryClient } from '@tanstack/react-query'

import { updateCampaignAction } from './campaign-action-api'
import { invalidateCampaignActionCache } from './invalidate-campaign-action-cache'
import type { CampaignAction, UpdateCampaignActionPayload } from './model'

export interface UpdateCampaignActionInput {
  id: string
  payload: UpdateCampaignActionPayload
}

/** PATCH writable CampaignAction fields; identity fields are absent by type. */
export function useUpdateCampaignAction(workspaceId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<CampaignAction, unknown, UpdateCampaignActionInput>({
    mutationFn: ({ id, payload }) => updateCampaignAction(id, payload),
    onSuccess: (action) =>
      invalidateCampaignActionCache(queryClient, workspaceId, action),
  })
}
