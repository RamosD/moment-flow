/**
 * Normalized HTTP/transport errors.
 *
 * Every error thrown by the API client is an `ApiError` (or a subclass), so
 * callers can `catch (e) { if (e instanceof ApiError) … }` and branch on the
 * specific type. Errors never carry the Authorization header or any token.
 */

export interface ApiErrorOptions {
  /** HTTP status code. `0` means the request never completed (network). */
  status: number
  /** Machine-readable code, e.g. DRF `code` or an internal label. */
  code?: string
  /** Parsed response body (safe to inspect; never contains request headers). */
  details?: unknown
  /** Correlation id from the response, when present. */
  requestId?: string
  /** Original error, when wrapping a thrown exception. */
  cause?: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly details?: unknown
  readonly requestId?: string

  constructor(message: string, options: ApiErrorOptions) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code
    this.details = options.details
    this.requestId = options.requestId
    if (options.cause !== undefined) {
      this.cause = options.cause
    }
    // Restore prototype chain for reliable `instanceof` after transpilation.
    Object.setPrototypeOf(this, new.target.prototype)
  }
}

/** 401 — not authenticated (missing/expired/invalid token). */
export class UnauthorizedError extends ApiError {
  constructor(message: string, options: Omit<ApiErrorOptions, 'status'>) {
    super(message, { ...options, status: 401 })
    this.name = 'UnauthorizedError'
  }
}

/** 403 — authenticated but not allowed (permission/workspace). */
export class ForbiddenError extends ApiError {
  constructor(message: string, options: Omit<ApiErrorOptions, 'status'>) {
    super(message, { ...options, status: 403 })
    this.name = 'ForbiddenError'
  }
}

/** 404 — resource not found (or not visible in the active workspace). */
export class NotFoundError extends ApiError {
  constructor(message: string, options: Omit<ApiErrorOptions, 'status'>) {
    super(message, { ...options, status: 404 })
    this.name = 'NotFoundError'
  }
}

/** Field-level validation failures keyed by field name. */
export type FieldErrors = Record<string, string[]>

/** 400 / 422 — request payload rejected by the backend. */
export class ValidationError extends ApiError {
  /** Per-field messages, best-effort parsed from the DRF error body. */
  readonly fieldErrors?: FieldErrors

  constructor(
    message: string,
    options: ApiErrorOptions & { fieldErrors?: FieldErrors },
  ) {
    super(message, options)
    this.name = 'ValidationError'
    this.fieldErrors = options.fieldErrors
  }
}

/** 502 / 503 — upstream/engine unavailable (retryable). */
export class ServiceUnavailableError extends ApiError {
  constructor(message: string, options: ApiErrorOptions) {
    super(message, options)
    this.name = 'ServiceUnavailableError'
  }
}

/** The request never reached/returned from the server (offline, DNS, CORS…). */
export class NetworkError extends ApiError {
  constructor(message: string, options?: Omit<ApiErrorOptions, 'status'>) {
    super(message, { ...options, status: 0 })
    this.name = 'NetworkError'
  }
}
