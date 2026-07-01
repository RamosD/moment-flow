import { useMutation, useQueryClient } from '@tanstack/react-query'

import { createCampaignAction } from './campaign-action-api'
import type { CampaignAction, CreateCampaignActionInput } from './model'
import { campaignActionKeys } from './query-keys'

/**
 * Create a campaign action against the real Backend Core endpoint for its type.
 * On success, invalidates the campaign-actions aggregate plus the underlying
 * resource lists (reports / media-kits) the War Room already renders, so every
 * surface refreshes. Errors propagate untouched for per-field 422 handling.
 */
export function useCreateCampaignAction(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  const queryClient = useQueryClient()

  return useMutation<CampaignAction, unknown, CreateCampaignActionInput>({
    mutationFn: (input) => createCampaignAction(input),
    onSuccess: (action) => {
      queryClient.invalidateQueries({
        queryKey: campaignActionKeys.byCampaign(workspaceId, campaignId ?? ''),
      })
      if (action.type === 'report_request') {
        queryClient.invalidateQueries({ queryKey: ['reports', workspaceId] })
      }
      if (action.type === 'media_kit_request') {
        queryClient.invalidateQueries({ queryKey: ['media-kits', workspaceId] })
      }
    },
  })
}
