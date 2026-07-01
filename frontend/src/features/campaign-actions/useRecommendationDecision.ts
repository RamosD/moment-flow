import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  createCampaignAction,
  fetchAllCampaignActionsByRecommendationType,
  invalidateCampaignActionCache,
} from '@/entities/campaign-action'
import type {
  CampaignAction,
} from '@/entities/campaign-action'
import { ValidationError } from '@/shared/api'
import type { UUID } from '@/shared/types'

import { findActiveRecommendationAction } from './recommendation-action-match'
import type { RecommendationActionDraft } from './recommendation-action-draft'
import { buildRecommendationDecisionPayload } from './recommendation-decision-payload'

export type RecommendationDecisionInput =
  | {
      action_type: 'mark_reviewed'
      campaign: UUID
      draft: RecommendationActionDraft
    }
  | {
      action_type: 'dismiss'
      campaign: UUID
      draft: RecommendationActionDraft
      dismiss_reason: string
    }

export interface RecommendationDecisionResult {
  campaignAction: CampaignAction
  created: boolean
}

function isDuplicateError(error: unknown): boolean {
  return (
    error instanceof ValidationError &&
    (error.fieldErrors?.recommendation_ref ?? []).some((message) =>
      /already exists|active action/i.test(message),
    )
  )
}

async function findExistingDecision(input: RecommendationDecisionInput) {
  const exact = await fetchAllCampaignActionsByRecommendationType(
    input.campaign,
    input.draft.recommendationRef.ref,
    input.action_type,
  )
  return findActiveRecommendationAction(exact.results, input.action_type)
}

async function invalidateDecisionCache(
  promise: Promise<unknown>,
): Promise<void> {
  try {
    await promise
  } catch {
    // A cache refetch failure must not turn a completed decision POST into an
    // apparent failure that invites a second dismiss/review write.
  }
}

/** Persist a recommendation-level reviewed/dismissed decision exactly once. */
export function useRecommendationDecision(workspaceId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<
    RecommendationDecisionResult,
    unknown,
    RecommendationDecisionInput
  >({
    mutationFn: async (input) => {
      if (!workspaceId) throw new Error('An active workspace is required.')

      const existing = await findExistingDecision(input)
      if (existing) {
        await invalidateDecisionCache(
          invalidateCampaignActionCache(
            queryClient,
            workspaceId,
            existing,
          ),
        )
        return { campaignAction: existing, created: false }
      }

      try {
        const campaignAction = await createCampaignAction(
          buildRecommendationDecisionPayload(input),
        )
        await invalidateDecisionCache(
          invalidateCampaignActionCache(
            queryClient,
            workspaceId,
            campaignAction,
          ),
        )
        return { campaignAction, created: true }
      } catch (error) {
        if (!isDuplicateError(error)) throw error

        // Another request may have won after the preflight. Refetch the exact
        // backend key and converge on its canonical CampaignAction.
        const concurrent = await findExistingDecision(input)
        if (!concurrent) throw error
        await invalidateDecisionCache(
          invalidateCampaignActionCache(
            queryClient,
            workspaceId,
            concurrent,
          ),
        )
        return { campaignAction: concurrent, created: false }
      }
    },
  })
}
