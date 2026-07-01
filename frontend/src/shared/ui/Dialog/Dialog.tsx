import { useEffect, useId, useRef } from 'react'
import type { MouseEvent, ReactNode } from 'react'

import { cx } from '@/shared/lib'

import { Button } from '../Button'
import styles from './Dialog.module.css'

export interface DialogProps {
  open: boolean
  /** Called on Escape, backdrop click, or the close button. Set `open` to false in response. */
  onClose: () => void
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  className?: string
}

/**
 * Accessible modal built on the native `<dialog>` element: the browser
 * supplies focus handling, top-layer stacking and Escape-to-close for free,
 * so no portal or focus-trap library is needed.
 *
 * All dismiss paths (Escape, backdrop click, close button) call `onClose`
 * exactly once and let the caller own the `open` state — the dialog never
 * closes itself without notifying the parent.
 */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  function handleBackdropClick(event: MouseEvent<HTMLDialogElement>) {
    // `<dialog>` has no separate backdrop node — a click that lands on the
    // dialog element itself (not on the inner content) is a backdrop click.
    if (event.target === ref.current) onClose()
  }

  function handleCancel(event: { preventDefault: () => void }) {
    // Escape fires the native `cancel` event. Prevent the browser's own close
    // so `open` stays the single source of truth, then notify the caller.
    event.preventDefault()
    onClose()
  }

  return (
    <dialog
      ref={ref}
      className={cx(styles.dialog, className)}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      onClick={handleBackdropClick}
      onCancel={handleCancel}
    >
      <div className={styles.content} onClick={(event) => event.stopPropagation()}>
        <div className={styles.head}>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          <Button variant="ghost" size="sm" aria-label="Close" onClick={onClose}>
            ×
          </Button>
        </div>
        {description && (
          <p id={descriptionId} className={styles.description}>
            {description}
          </p>
        )}
        <div className={styles.body}>{children}</div>
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </dialog>
  )
}
