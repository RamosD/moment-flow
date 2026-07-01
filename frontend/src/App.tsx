import { AppProviders } from '@/app/providers'
import { AppRouter } from '@/app/router'

/**
 * Composition root: global providers wrap the router.
 *
 * Auth + Workspace are initial foundations (FE-004); the full login flow and
 * workspace loading arrive in FE-007 / FE-008.
 */
function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  )
}

export default App
