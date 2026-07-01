import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { LoadingState } from '@/shared/ui'

import { useAuth } from './useAuth'

/**
 * Route guard. Renders nested routes only when authenticated; shows a loading
 * state while the session is being restored, and redirects to /login otherwise
 * (preserving the attempted path so login can return the user to it).
 */
export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <LoadingState label="Checking your session…" />
  }
  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
