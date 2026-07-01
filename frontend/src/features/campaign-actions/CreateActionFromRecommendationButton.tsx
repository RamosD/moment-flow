import { useState } from 'react'

import type { Campaign, CampaignRecommendation } from '@/entities/campaign'
import type { CampaignAction } from '@/entities/campaign-action'
import { Button } from '@/shared/ui'

import { CreateActionFromRecommendationDialog } from './CreateActionFromRecommendationDialog'
import { RecommendationActionState } from './RecommendationActionState'
import { matchRecommendationAction } from './recommendation-action-match'
import { useRecommendationActionDraft } from './useRecommendationActionDraft'
import styles from './campaign-actions.module.css'

interface CreateActionFromRecommendationButtonProps {
  workspaceId: string | null
  /** Source campaign. Undefined while loading — the affordance disables itself. */
  campaign: Campaign | undefined
  recommendation: CampaignRecommendation
  index: number
  /** Already-created campaign actions, for duplicate detection (CA-009). */
  actions: CampaignAction[] | undefined
}

/**
 * Per-recommendation execution affordance (CA-006).
 *
 * Renders one of three states:
 *  - a read-only status indicator when a matching action already exists
 *    (avoids obvious duplication);
 *  - a "Create action" button that opens the confirm dialog;
 *  - a disabled button while the campaign is still loading.
 *
 * Recommendations are never converted automatically — creation always requires
 * the user to confirm in the dialog.
 */
export function CreateActionFromRecommendationButton({
  workspaceId,
  campaign,
  recommendation,
  index,
  actions,
}: CreateActionFromRecommendationButtonProps) {
  const [open, setOpen] = useState(false)
  const draft = useRecommendationActionDraft(campaign?.id, recommendation, index)
  const matched = matchRecommendationAction(draft, actions)

  if (matched) {
    return <RecommendationActionState action={matched} />
  }

  const ready = Boolean(campaign && draft)

  return (
    <span className={styles.affordance}>
      <Button
        variant="secondary"
        size="sm"
        disabled={!ready}
        onClick={() => setOpen(true)}
      >
        Create action
      </Button>
      {ready && draft && campaign && (
        <CreateActionFromRecommendationDialog
          open={open}
          onClose={() => setOpen(false)}
          draft={draft}
          campaign={campaign}
          workspaceId={workspaceId}
        />
      )}
    </span>
  )
}
