import { apiClient } from '@/shared/api'
import type { User } from '@/entities/user'

export interface LoginCredentials {
  email: string
  password: string
}

/** Response of `POST /auth/token/`. */
export interface TokenPair {
  access: string
  refresh: string
}

/**
 * Response of `POST /auth/token/refresh/`. The schema marks `refresh` as
 * write-only, so the documented response is `{ access }`. We read `refresh`
 * defensively in case the backend rotates refresh tokens (see report).
 */
export interface RefreshResult {
  access: string
  refresh?: string
}

/** Exchange email + password for a token pair. Unauthenticated request. */
export function login(credentials: LoginCredentials): Promise<TokenPair> {
  return apiClient.post<TokenPair>('/auth/token/', credentials, { auth: false })
}

/** Exchange a refresh token for a fresh access token. Unauthenticated request. */
export function refreshAccessToken(refresh: string): Promise<RefreshResult> {
  return apiClient.post<RefreshResult>(
    '/auth/token/refresh/',
    { refresh },
    { auth: false },
  )
}

/** Fetch the authenticated user's profile. Requires a valid access token. */
export function fetchCurrentUser(): Promise<User> {
  return apiClient.get<User>('/auth/me/')
}
