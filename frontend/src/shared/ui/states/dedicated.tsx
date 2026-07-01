import type { ReactNode } from 'react'

import { Button } from '../Button'
import { FeedbackBlock } from './FeedbackBlock'

/**
 * Dedicated, semantic state screens for the common API/session/permission
 * outcomes. Each is a thin, consistent wrapper over FeedbackBlock with fixed,
 * non-technical copy. Actions are render-props so these stay free of router
 * dependencies. None of them ever surface tokens or raw error details.
 */

/** 401 — the session is no longer valid. */
export function SessionExpired({
  action,
  className,
}: {
  action?: ReactNode
  className?: string
}) {
  return (
    <FeedbackBlock
      tone="danger"
      title="Session expired"
      description="Your session is no longer valid. Please sign in again."
      actions={action}
      className={className}
    />
  )
}

/** 403 — authenticated but not allowed. */
export function PermissionDenied({
  description = 'You do not have permission to view this in the current workspace.',
  action,
  className,
}: {
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <FeedbackBlock
      tone="danger"
      title="Access denied"
      description={description}
      actions={action}
      className={className}
    />
  )
}

/** 404 — resource missing or not visible here. */
export function NotFoundState({
  title = 'Not found',
  description = 'This resource does not exist or is not available here.',
  action,
  className,
}: {
  title?: string
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <FeedbackBlock
      tone="neutral"
      icon="?"
      title={title}
      description={description}
      actions={action}
      className={className}
    />
  )
}

/** 502 / 503 — upstream/engine temporarily unavailable. */
export function ServiceUnavailable({
  onRetry,
  className,
}: {
  onRetry?: () => void
  className?: string
}) {
  return (
    <FeedbackBlock
      tone="warning"
      title="Service unavailable"
      description="The service is temporarily unavailable. Please try again shortly."
      actions={
        onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Try again
          </Button>
        )
      }
      className={className}
    />
  )
}

/** No active workspace — the user must pick one before continuing. */
export function WorkspaceRequiredState({
  description = 'Choose a workspace from the top bar to continue.',
  action,
  className,
}: {
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <FeedbackBlock
      tone="neutral"
      title="No workspace selected"
      description={description}
      actions={action}
      className={className}
    />
  )
}
