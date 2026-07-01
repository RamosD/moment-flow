import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import { setTokenProvider, setUnauthorizedHandler } from '@/shared/api'
import type { User } from '@/entities/user'

import {
  fetchCurrentUser,
  login as loginRequest,
  refreshAccessToken,
} from './auth-api'
import type { LoginCredentials } from './auth-api'
import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context'
import {
  clearRefreshToken,
  persistRefreshToken,
  readRefreshToken,
} from './token-storage'

/**
 * Auth/session foundation.
 *
 * - Access token lives in a ref (memory) and is exposed to the API client via
 *   the injectable token provider.
 * - Refresh token is persisted (token-storage) to restore the session on boot.
 * - A global 401 handler clears the session so ProtectedRoute can redirect.
 *
 * The Backend Core remains the source of truth for permissions; this only
 * manages session presence, not business authorization (no RBAC here).
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  // Start in `loading` only when there is a refresh token to restore from;
  // otherwise we are plainly unauthenticated (and the boot effect is a no-op).
  const [status, setStatus] = useState<AuthStatus>(() =>
    readRefreshToken() ? 'loading' : 'unauthenticated',
  )
  const [user, setUser] = useState<User | null>(null)
  // True after the session was cleared by a 401 (expiry), so the login screen
  // can explain why. Reset on a successful login.
  const [sessionExpired, setSessionExpired] = useState(false)
  const accessTokenRef = useRef<string | null>(null)

  // Expose the (in-memory) access token to the API client.
  useEffect(() => {
    setTokenProvider(() => accessTokenRef.current)
  }, [])

  const clearSession = useCallback(() => {
    accessTokenRef.current = null
    clearRefreshToken()
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  // Load the profile in the background; never blocks session state.
  const loadUser = useCallback(async () => {
    try {
      setUser(await fetchCurrentUser())
    } catch {
      // A 401 here is handled globally (clears session); other errors are
      // non-fatal — the session is valid even without the profile loaded.
      setUser(null)
    }
  }, [])

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const tokens = await loginRequest(credentials)
      accessTokenRef.current = tokens.access
      persistRefreshToken(tokens.refresh)
      setSessionExpired(false)
      setStatus('authenticated')
      void loadUser()
    },
    [loadUser],
  )

  const logout = useCallback(() => {
    setSessionExpired(false)
    clearSession()
  }, [clearSession])

  // Global 401 handler: an authenticated request was refused → the session
  // expired. Flag it (for the login screen) and clear the session; the
  // ProtectedRoute then redirects to /login.
  const handleUnauthorized = useCallback(() => {
    setSessionExpired(true)
    clearSession()
  }, [clearSession])

  useEffect(() => {
    setUnauthorizedHandler(handleUnauthorized)
  }, [handleUnauthorized])

  // Boot: restore a session from a stored refresh token, if any.
  useEffect(() => {
    const stored = readRefreshToken()
    if (!stored) return
    let cancelled = false
    refreshAccessToken(stored)
      .then((result) => {
        if (cancelled) return
        accessTokenRef.current = result.access
        if (result.refresh) persistRefreshToken(result.refresh)
        setStatus('authenticated')
        void loadUser()
      })
      .catch(() => {
        if (!cancelled) clearSession()
      })
    return () => {
      cancelled = true
    }
  }, [clearSession, loadUser])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, sessionExpired, login, logout }),
    [status, user, sessionExpired, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
