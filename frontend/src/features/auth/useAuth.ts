import { useContext } from 'react'

import { AuthContext, type AuthContextValue } from './auth-context'

/** Access the auth/session context. Must be used within <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
