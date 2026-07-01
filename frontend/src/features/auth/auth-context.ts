import { createContext } from 'react'

import type { User } from '@/entities/user'

import type { LoginCredentials } from './auth-api'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export interface AuthContextValue {
  /** `loading` while the session is being restored on boot. */
  status: AuthStatus
  /** The authenticated user, when loaded. */
  user: User | null
  /** True when the session was just ended by a 401 (token expiry/refusal). */
  sessionExpired: boolean
  /** Exchange credentials for a session. Throws on invalid credentials. */
  login: (credentials: LoginCredentials) => Promise<void>
  /** Clear the session (local only; JWTs are stateless). */
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
