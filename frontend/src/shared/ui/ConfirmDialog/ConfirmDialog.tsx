import { Button } from '../Button'
import type { ButtonVariant } from '../Button'
import { Dialog } from '../Dialog'

export interface ConfirmDialogProps {
  open: boolean
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  confirmVariant?: ButtonVariant
  /** Disables both buttons and swaps the confirm label while a request is in flight. */
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Confirm/cancel prompt built on {@link Dialog}. Intended for actions that
 * need an explicit confirmation step (e.g. a future dismiss-with-reason
 * flow) — not used for plain informational dialogs.
 */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  confirmVariant = 'primary',
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      title={title}
      description={message}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} disabled={busy}>
            {busy ? 'Working…' : confirmLabel}
          </Button>
        </>
      }
    />
  )
}
