import type { ReactNode } from 'react'

import {
  ForbiddenError,
  NotFoundError,
  ServiceUnavailableError,
  UnauthorizedError,
} from '@/shared/api'

import { Button } from '../Button'
import {
  NotFoundState,
  PermissionDenied,
  ServiceUnavailable,
  SessionExpired,
} from './dedicated'
import { FeedbackBlock } from './FeedbackBlock'
import { resolveErrorPreset } from './error-presets'

export interface ErrorStateProps {
  /**
   * The thrown error. When provided (and no explicit title/description), it is
   * routed to the right dedicated screen: 401 → SessionExpired, 403 →
   * PermissionDenied, 404 → NotFoundState, 502/503 → ServiceUnavailable.
   * Everything else (network / 422 / 500 / unknown) gets a generic block with
   * standard, non-technical copy.
   */
  error?: unknown
  title?: string
  description?: string
  /** Retry handler; renders a "Try again" action when present. */
  onRetry?: () => void
  retryLabel?: string
  /** Extra actions (e.g. "Sign in", "Go back"). */
  action?: ReactNode
  className?: string
}

/**
 * Transversal error screen. Pass an `error` for standard, type-aware messaging,
 * or explicit `title`/`description` for custom cases. Never surfaces tokens or
 * raw stack traces — only normalized, user-facing copy.
 */
export function ErrorState({
  error,
  title,
  description,
  onRetry,
  retryLabel = 'Try again',
  action,
  className,
}: ErrorStateProps) {
  // Route known error types to their dedicated screen, unless the caller
  // overrode the copy explicitly.
  if (error !== undefined && title === undefined && description === undefined) {
    if (error instanceof UnauthorizedError) {
      return <SessionExpired action={action} className={className} />
    }
    if (error instanceof ForbiddenError) {
      return <PermissionDenied action={action} className={className} />
    }
    if (error instanceof NotFoundError) {
      return <NotFoundState action={action} className={className} />
    }
    if (error instanceof ServiceUnavailableError) {
      return <ServiceUnavailable onRetry={onRetry} className={className} />
    }
  }

  const preset = error !== undefined ? resolveErrorPreset(error) : undefined
  const resolvedTitle = title ?? preset?.title ?? 'Something went wrong'
  const resolvedDescription = description ?? preset?.description

  return (
    <FeedbackBlock
      tone="danger"
      title={resolvedTitle}
      description={resolvedDescription}
      className={className}
      actions={
        (onRetry || action) && (
          <>
            {onRetry && (
              <Button variant="secondary" size="sm" onClick={onRetry}>
                {retryLabel}
              </Button>
            )}
            {action}
          </>
        )
      }
    />
  )
}
