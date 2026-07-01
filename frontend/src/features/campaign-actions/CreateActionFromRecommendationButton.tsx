import { useState } from 'react'

import type { Campaign, CampaignRecommendation } from '@/entities/campaign'
import { useCampaignActionsByRecommendation } from '@/entities/campaign-action'
import { Button } from '@/shared/ui'

import { CreateActionFromRecommendationDialog } from './CreateActionFromRecommendationDialog'
import { RecommendationDecisionActions } from './RecommendationDecisionActions'
import { RecommendationActionState } from './RecommendationActionState'
import { matchRecommendationActions } from './recommendation-action-match'
import { useRecommendationActionDraft } from './useRecommendationActionDraft'
import styles from './campaign-actions.module.css'

interface CreateActionFromRecommendationButtonProps {
  workspaceId: string | null
  campaign: Campaign | undefined
  recommendation: CampaignRecommendation
  index: number
}

/**
 * Recommendation affordance backed by an exact CampaignAction lookup.
 * The lookup is isolated from the rest of the intelligence panel: failure only
 * disables creation until duplicate state can be checked safely.
 */
export function CreateActionFromRecommendationButton({
  workspaceId,
  campaign,
  recommendation,
  index,
}: CreateActionFromRecommendationButtonProps) {
  const [open, setOpen] = useState(false)
  const draft = useRecommendationActionDraft(campaign?.id, recommendation, index)
  const actionsQuery = useCampaignActionsByRecommendation(
    workspaceId,
    campaign?.id,
    draft?.recommendationRef.ref,
  )
  const actions = matchRecommendationActions(
    draft,
    actionsQuery.data?.results,
  )
  const actionCount = actionsQuery.data?.count ?? 0
  const hasActions = actionCount > 0
  const lookupReady = !actionsQuery.isPending && !actionsQuery.isError
  const ready = Boolean(campaign && draft && lookupReady)

  return (
    <div className={styles.affordance}>
      {hasActions && (
        <RecommendationActionState
          actions={actions}
          totalCount={actionCount}
        />
      )}
      <Button
        variant="secondary"
        size="sm"
        disabled={!ready}
        title={
          actionsQuery.isError
            ? 'Could not verify existing campaign actions.'
            : undefined
        }
        onClick={() => setOpen(true)}
      >
        {hasActions ? 'Create another action' : 'Create action'}
      </Button>
      {ready && draft && campaign && (
        <RecommendationDecisionActions
          workspaceId={workspaceId}
          campaign={campaign}
          draft={draft}
          actions={actions}
        />
      )}
      {open && ready && draft && campaign && (
        <CreateActionFromRecommendationDialog
          open
          onClose={() => setOpen(false)}
          draft={draft}
          campaign={campaign}
          workspaceId={workspaceId}
        />
      )}
    </div>
  )
}
