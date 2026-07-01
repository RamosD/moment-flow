import { useId, useState } from 'react'
import type { FormEvent } from 'react'

import type { Campaign } from '@/entities/campaign'
import { ValidationError } from '@/shared/api'
import {
  Alert,
  Button,
  Dialog,
  FormField,
  resolveErrorPreset,
  Textarea,
} from '@/shared/ui'

import type { RecommendationActionDraft } from './recommendation-action-draft'
import { useRecommendationDecision } from './useRecommendationDecision'
import styles from './campaign-actions.module.css'

interface DismissRecommendationDialogProps {
  open: boolean
  onClose: () => void
  workspaceId: string | null
  campaign: Campaign
  draft: RecommendationActionDraft
}

export function DismissRecommendationDialog({
  open,
  onClose,
  workspaceId,
  campaign,
  draft,
}: DismissRecommendationDialogProps) {
  const formId = useId()
  const [dismissReason, setDismissReason] = useState('')
  const [localError, setLocalError] = useState<string>()
  const mutation = useRecommendationDecision(workspaceId)
  const backendReasonError =
    mutation.error instanceof ValidationError
      ? mutation.error.fieldErrors?.dismiss_reason?.join(' ')
      : undefined
  const generalError =
    mutation.error && !backendReasonError
      ? resolveErrorPreset(mutation.error)
      : null

  function handleClose() {
    if (mutation.isPending) return
    mutation.reset()
    setLocalError(undefined)
    onClose()
  }

  function handleSuccess() {
    setLocalError(undefined)
    onClose()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (mutation.isPending) return

    const reason = dismissReason.trim()
    if (!reason) {
      setLocalError('Dismiss reason is required.')
      return
    }

    setLocalError(undefined)
    mutation.mutate(
      {
        action_type: 'dismiss',
        campaign: campaign.id,
        draft,
        dismiss_reason: reason,
      },
      { onSuccess: handleSuccess },
    )
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Dismiss recommendation"
      description="Record a persistent dismissed CampaignAction. This decision remains visible after reload."
    >
      <form className={styles.form} onSubmit={handleSubmit}>
        {generalError && (
          <Alert variant="danger" title={generalError.title}>
            {generalError.description}
          </Alert>
        )}
        <FormField
          label="Dismiss reason"
          htmlFor={`${formId}-reason`}
          required
          error={localError ?? backendReasonError}
          hint="Stored in the canonical dismiss_reason field."
        >
          <Textarea
            id={`${formId}-reason`}
            value={dismissReason}
            disabled={mutation.isPending}
            onChange={(event) => setDismissReason(event.target.value)}
          />
        </FormField>
        <div className={styles.formActions}>
          <Button
            type="button"
            variant="secondary"
            disabled={mutation.isPending}
            onClick={handleClose}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="danger"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Dismissing…' : 'Dismiss recommendation'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
