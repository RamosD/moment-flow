import { useState } from 'react'

import type { Campaign } from '@/entities/campaign'
import type { CampaignAction } from '@/entities/campaign-action'
import { Button, resolveErrorPreset } from '@/shared/ui'

import { DismissRecommendationDialog } from './DismissRecommendationDialog'
import { findActiveRecommendationAction } from './recommendation-action-match'
import type { RecommendationActionDraft } from './recommendation-action-draft'
import { useRecommendationDecision } from './useRecommendationDecision'
import styles from './campaign-actions.module.css'

interface RecommendationDecisionActionsProps {
  workspaceId: string | null
  campaign: Campaign
  draft: RecommendationActionDraft
  actions: CampaignAction[]
}

export function RecommendationDecisionActions({
  workspaceId,
  campaign,
  draft,
  actions,
}: RecommendationDecisionActionsProps) {
  const [dismissOpen, setDismissOpen] = useState(false)
  const markReviewed = useRecommendationDecision(workspaceId)
  const reviewedAction = findActiveRecommendationAction(
    actions,
    'mark_reviewed',
  )
  const markError = markReviewed.error
    ? resolveErrorPreset(markReviewed.error)
    : null

  function handleMarkReviewed() {
    if (markReviewed.isPending || reviewedAction) return
    markReviewed.mutate({
      action_type: 'mark_reviewed',
      campaign: campaign.id,
      draft,
    })
  }

  return (
    <>
      <span className={styles.decisionActions}>
        <Button
          variant="success"
          size="sm"
          disabled={markReviewed.isPending || Boolean(reviewedAction)}
          onClick={handleMarkReviewed}
        >
          {markReviewed.isPending
            ? 'Marking…'
            : reviewedAction
              ? 'Reviewed'
              : 'Mark reviewed'}
        </Button>
        <Button
          variant="danger"
          size="sm"
          disabled={markReviewed.isPending}
          onClick={() => setDismissOpen(true)}
        >
          Dismiss
        </Button>
      </span>
      {markError && (
        <span className={styles.decisionError} role="alert">
          {markError.title}: {markError.description}
        </span>
      )}
      {dismissOpen && (
        <DismissRecommendationDialog
          open
          onClose={() => setDismissOpen(false)}
          workspaceId={workspaceId}
          campaign={campaign}
          draft={draft}
        />
      )}
    </>
  )
}
