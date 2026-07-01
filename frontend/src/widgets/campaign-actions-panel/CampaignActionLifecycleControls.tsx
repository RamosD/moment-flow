import { useState } from 'react'

import type { CampaignAction } from '@/entities/campaign-action'
import {
  availablePanelTransitions,
  buildCampaignActionRetryPayload,
  useCampaignActionTransition,
  useCreateCampaignAction,
} from '@/entities/campaign-action'
import { Button, ConfirmDialog, resolveErrorPreset } from '@/shared/ui'

import { DismissCampaignActionDialog } from './DismissCampaignActionDialog'
import styles from './CampaignActionsPanel.module.css'

interface CampaignActionLifecycleControlsProps {
  action: CampaignAction
  workspaceId: string | null
}

export function CampaignActionLifecycleControls({
  action,
  workspaceId,
}: CampaignActionLifecycleControlsProps) {
  const [cancelOpen, setCancelOpen] = useState(false)
  const [dismissOpen, setDismissOpen] = useState(false)
  const transition = useCampaignActionTransition(workspaceId)
  const retry = useCreateCampaignAction(workspaceId)
  const available = availablePanelTransitions(action.status)
  const retryPayload = buildCampaignActionRetryPayload(action)
  const busy = transition.isPending || retry.isPending
  const error = transition.error ?? retry.error
  const errorPreset = error ? resolveErrorPreset(error) : null
  const transitionErrorPreset = transition.error
    ? resolveErrorPreset(transition.error)
    : null

  function completeAction() {
    if (busy || !available.includes('complete')) return
    transition.mutate({ id: action.id, transition: 'complete' })
  }

  function cancelAction() {
    if (busy || !available.includes('cancel')) return
    transition.mutate(
      { id: action.id, transition: 'cancel' },
      { onSuccess: () => setCancelOpen(false) },
    )
  }

  function retryAction() {
    if (busy || !retryPayload) return
    retry.mutate(retryPayload)
  }

  if (available.length === 0 && !retryPayload && !errorPreset) return null

  return (
    <div className={styles.lifecycle}>
      <div className={styles.lifecycleActions}>
        {available.includes('complete') && (
          <Button
            variant="success"
            size="sm"
            disabled={busy}
            onClick={completeAction}
          >
            {transition.isPending ? 'Updating…' : 'Complete'}
          </Button>
        )}
        {available.includes('dismiss') && (
          <Button
            variant="danger"
            size="sm"
            disabled={busy}
            onClick={() => setDismissOpen(true)}
          >
            Dismiss
          </Button>
        )}
        {available.includes('cancel') && (
          <Button
            variant="secondary"
            size="sm"
            disabled={busy}
            onClick={() => setCancelOpen(true)}
          >
            Cancel
          </Button>
        )}
        {retryPayload && (
          <Button
            variant="secondary"
            size="sm"
            disabled={busy || Boolean(retry.data)}
            title="Create a new CampaignAction; the failed action stays unchanged."
            onClick={retryAction}
          >
            {retry.isPending
              ? 'Retrying…'
              : retry.data
                ? 'New action created'
                : 'Retry as new action'}
          </Button>
        )}
      </div>
      {errorPreset && (
        <span className={styles.lifecycleError} role="alert">
          {errorPreset.title}: {errorPreset.description}
        </span>
      )}
      {cancelOpen && (
        <ConfirmDialog
          open
          title="Cancel campaign action"
          message={
            transitionErrorPreset
              ? `${transitionErrorPreset.title}: ${transitionErrorPreset.description}`
              : `Cancel “${action.title}” permanently? This action cannot be reopened.`
          }
          confirmLabel="Cancel action"
          confirmVariant="danger"
          busy={transition.isPending}
          onConfirm={cancelAction}
          onCancel={() => {
            if (!transition.isPending) setCancelOpen(false)
          }}
        />
      )}
      {dismissOpen && (
        <DismissCampaignActionDialog
          action={action}
          workspaceId={workspaceId}
          open
          onClose={() => setDismissOpen(false)}
        />
      )}
    </div>
  )
}
