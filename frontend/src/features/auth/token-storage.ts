/**
 * Token persistence for the MVP.
 *
 * - The **access** token lives only in memory (held by the AuthProvider). It is
 *   never persisted.
 * - The **refresh** token is persisted in localStorage so the session can be
 *   restored after a page reload (boot → refresh → new access token).
 *
 * LIMITATION (FE-PDEC-003): a refresh token in localStorage is readable by
 * any script and is therefore exposed to XSS. This is an accepted tradeoff for
 * a controlled technical pilot. For production, move to an httpOnly, Secure,
 * SameSite cookie issued by the Backend Core.
 */

const REFRESH_TOKEN_KEY = 'mf.refresh_token'

export function readRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function persistRefreshToken(token: string): void {
  try {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  } catch {
    // Ignore storage failures (private mode, quota); session stays in memory.
  }
}

export function clearRefreshToken(): void {
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  } catch {
    // Ignore.
  }
}
