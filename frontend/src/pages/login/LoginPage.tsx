import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/features/auth'
import { APP_CONFIG } from '@/app/config'
import { ApiError } from '@/shared/api'
import { Alert, Button, Card } from '@/shared/ui'

import styles from './LoginPage.module.css'

function readRedirectTarget(state: unknown): string {
  if (state && typeof state === 'object' && 'from' in state) {
    const from = (state as { from?: unknown }).from
    if (typeof from === 'string' && from) return from
  }
  return '/'
}

/** Minimal email/password sign-in for the MVP. */
export function LoginPage() {
  const { login, status, sessionExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = readRedirectTarget(location.state)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Already signed in (e.g. navigated to /login manually) → bounce away.
  if (status === 'authenticated') {
    return <Navigate to={redirectTo} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login({ email, password })
      navigate(redirectTo, { replace: true })
    } catch (err) {
      const invalidCredentials =
        err instanceof ApiError && (err.status === 401 || err.status === 400)
      setError(
        invalidCredentials
          ? 'Invalid email or password.'
          : 'Could not sign in. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.wrapper}>
      <Card padding="lg" className={styles.card}>
        <div className={styles.head}>
          <span className={styles.brand}>{APP_CONFIG.name}</span>
          <span className={styles.subtitle}>Sign in to {APP_CONFIG.productName}</span>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {error ? (
            <Alert variant="danger">{error}</Alert>
          ) : (
            sessionExpired && (
              <Alert variant="info">
                Your session has expired. Please sign in again.
              </Alert>
            )
          )}

          <div className={styles.field}>
            <label className={styles.label} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <Button type="submit" fullWidth disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
