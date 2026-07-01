import {
  ApiError,
  ForbiddenError,
  NetworkError,
  NotFoundError,
  ServiceUnavailableError,
  UnauthorizedError,
  ValidationError,
} from '../../api/errors.ts'

export interface ErrorStatePreset {
  title: string
  description: string
}

/**
 * Map a thrown error to user-facing copy. Centralizes the standard patterns
 * (network / 401 / 403 / 404 / service unavailable / validation) so every
 * screen shows consistent, non-technical messages. Never surfaces tokens or
 * raw stack traces.
 */
export function resolveErrorPreset(error: unknown): ErrorStatePreset {
  if (error instanceof NetworkError) {
    return {
      title: 'Connection problem',
      description:
        'We could not reach the server. Check your connection and try again.',
    }
  }
  if (error instanceof UnauthorizedError) {
    return {
      title: 'Session expired',
      description: 'Your session is no longer valid. Please sign in again.',
    }
  }
  if (error instanceof ForbiddenError) {
    return {
      title: 'Access denied',
      description: 'You do not have permission to view this in this workspace.',
    }
  }
  if (error instanceof NotFoundError) {
    return {
      title: 'Not found',
      description: 'This resource does not exist or is not available here.',
    }
  }
  if (error instanceof ServiceUnavailableError) {
    return {
      title: 'Service unavailable',
      description:
        'The service is temporarily unavailable. Please try again shortly.',
    }
  }
  if (error instanceof ValidationError) {
    // Field-level details are surfaced inline; the general alert always uses
    // generic copy so HTTP status text ("Unprocessable Content") never leaks.
    return {
      title: 'Invalid request',
      description: 'Some of the submitted data was rejected.',
    }
  }
  if (error instanceof ApiError) {
    return {
      title: 'Something went wrong',
      description: error.message || 'An unexpected server error occurred.',
    }
  }
  return {
    title: 'Something went wrong',
    description: 'An unexpected error occurred. Please try again.',
  }
}
