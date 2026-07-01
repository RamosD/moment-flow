/**
 * Transport-level types shared by all API access.
 */

/** Standard DRF page envelope used across the Backend Core list endpoints. */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Getter for the current access token. Returns null/undefined when signed out. */
export type TokenProvider = () => string | null | undefined

/** Getter for the active workspace id (UUID). Null/undefined when none selected. */
export type WorkspaceProvider = () => string | null | undefined

/** Per-request options accepted by the client helpers. */
export interface RequestOptions {
  /** Query string parameters; undefined/null values are skipped. */
  params?: Record<string, string | number | boolean | null | undefined>
  /** Extra headers (merged last). Internal-secret headers are stripped. */
  headers?: Record<string, string>
  /** Abort signal for cancellation/timeouts. */
  signal?: AbortSignal
  /**
   * Set false to skip the Authorization header (e.g. login/refresh calls).
   * Defaults to true.
   */
  auth?: boolean
}
