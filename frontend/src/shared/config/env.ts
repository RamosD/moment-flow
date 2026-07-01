/**
 * Environment configuration for the frontend.
 *
 * Lives in `shared` (not `app`) so the API client can consume it without
 * breaking the layer rule (`shared` must not import from `app`).
 *
 * The ONLY backend the frontend talks to is the Backend Core, addressed by
 * `VITE_BACKEND_API_BASE_URL`. There is intentionally no configuration here for
 * the Intelligence Engine or the Content Renderer, and no internal secrets.
 */

/** Sensible default for local development against a Backend Core on :8000. */
const DEV_FALLBACK_API_BASE_URL = 'http://localhost:8000/api/v1'

class EnvConfigError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'EnvConfigError'
  }
}

function isValidHttpUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

/** Remove a single trailing slash so paths can be joined predictably. */
function stripTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function resolveApiBaseUrl(): string {
  const raw = import.meta.env.VITE_BACKEND_API_BASE_URL?.trim()

  if (!raw) {
    if (import.meta.env.DEV) {
      // Loud but harmless: no secrets involved, only a public base URL.
      console.warn(
        `[config] VITE_BACKEND_API_BASE_URL is not set. Falling back to ` +
          `"${DEV_FALLBACK_API_BASE_URL}" (development only).`,
      )
      return stripTrailingSlash(DEV_FALLBACK_API_BASE_URL)
    }
    throw new EnvConfigError(
      'VITE_BACKEND_API_BASE_URL is required but was not provided.',
    )
  }

  if (!isValidHttpUrl(raw)) {
    throw new EnvConfigError(
      `VITE_BACKEND_API_BASE_URL is not a valid http(s) URL: "${raw}".`,
    )
  }

  return stripTrailingSlash(raw)
}

export const ENV = {
  /** Backend Core API base URL, without a trailing slash. */
  apiBaseUrl: resolveApiBaseUrl(),
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const

export type Env = typeof ENV
