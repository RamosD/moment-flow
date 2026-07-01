import { useId, useState } from 'react'
import type { FormEvent } from 'react'

import type { CampaignAction } from '@/entities/campaign-action'
import { useCampaignActionTransition } from '@/entities/campaign-action'
import { ValidationError } from '@/shared/api'
import {
  Alert,
  Button,
  Dialog,
  FormField,
  resolveErrorPreset,
  Textarea,
} from '@/shared/ui'

import styles from './CampaignActionsPanel.module.css'

interface DismissCampaignActionDialogProps {
  action: CampaignAction
  workspaceId: string | null
  open: boolean
  onClose: () => void
}

export function DismissCampaignActionDialog({
  action,
  workspaceId,
  open,
  onClose,
}: DismissCampaignActionDialogProps) {
  const fieldId = useId()
  const [reason, setReason] = useState('')
  const [localError, setLocalError] = useState<string>()
  const mutation = useCampaignActionTransition(workspaceId)
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (mutation.isPending) return

    const dismissReason = reason.trim()
    if (!dismissReason) {
      setLocalError('Dismiss reason is required.')
      return
    }

    setLocalError(undefined)
    mutation.mutate(
      {
        id: action.id,
        transition: 'dismiss',
        payload: { dismiss_reason: dismissReason },
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Dismiss campaign action"
      description={`Dismiss “${action.title}” permanently. This action cannot be reopened.`}
    >
      <form className={styles.dialogForm} onSubmit={handleSubmit}>
        {generalError && (
          <Alert variant="danger" title={generalError.title}>
            {generalError.description}
          </Alert>
        )}
        <FormField
          label="Dismiss reason"
          htmlFor={`${fieldId}-reason`}
          required
          error={localError ?? backendReasonError}
        >
          <Textarea
            id={`${fieldId}-reason`}
            value={reason}
            disabled={mutation.isPending}
            onChange={(event) => setReason(event.target.value)}
          />
        </FormField>
        <div className={styles.dialogActions}>
          <Button
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
            {mutation.isPending ? 'Dismissing…' : 'Dismiss action'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
