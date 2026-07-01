import { useMutation, useQueryClient } from '@tanstack/react-query'

import { updateCampaignAction } from './campaign-action-api'
import type { CampaignAction, UpdateCampaignActionInput } from './model'
import { campaignActionKeys } from './query-keys'

/**
 * Update a campaign action (reports / media kits only — content-pack-requests
 * are immutable, see CAMPAIGN_ACTION_CAPABILITIES). On success, invalidates the
 * campaign-actions aggregate and the matching resource list.
 */
export function useUpdateCampaignAction(
  workspaceId: string | null,
  campaignId: string | undefined,
) {
  const queryClient = useQueryClient()

  return useMutation<CampaignAction, unknown, UpdateCampaignActionInput>({
    mutationFn: (input) => updateCampaignAction(input),
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
