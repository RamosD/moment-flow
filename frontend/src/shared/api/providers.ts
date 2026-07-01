/**
 * Injectable providers for request-time credentials.
 *
 * The access token and active workspace id are NOT hardcoded and NOT imported
 * from upper layers. Instead, higher layers (AuthProvider in FE-007,
 * WorkspaceProvider in FE-008) register getter functions here, and the default
 * API client reads through them at request time. This keeps `shared` free of
 * dependencies on `app`/`features` while still letting them drive auth state.
 */

import type { TokenProvider, WorkspaceProvider } from './types'

let tokenProvider: TokenProvider = () => null
let workspaceProvider: WorkspaceProvider = () => null
let unauthorizedHandler: () => void = () => {}

/** Register the function that returns the current access token. */
export function setTokenProvider(provider: TokenProvider): void {
  tokenProvider = provider
}

/** Register the function that returns the active workspace id. */
export function setWorkspaceProvider(provider: WorkspaceProvider): void {
  workspaceProvider = provider
}

/** Read the current access token (used by the default client). */
export function readToken(): string | null | undefined {
  return tokenProvider()
}

/** Read the active workspace id (used by the default client). */
export function readWorkspaceId(): string | null | undefined {
  return workspaceProvider()
}

/**
 * Register a handler invoked when an *authenticated* request is rejected with
 * 401 (the session token was refused). The AuthProvider (FE-007) uses this to
 * clear the session globally. Login/refresh calls use `auth: false` and are
 * intentionally excluded so a failed login does not trigger a global logout.
 */
export function setUnauthorizedHandler(handler: () => void): void {
  unauthorizedHandler = handler
}

/** Invoke the registered unauthorized handler (used by the client on 401). */
export function notifyUnauthorized(): void {
  unauthorizedHandler()
}
