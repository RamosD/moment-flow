import { RouterProvider } from 'react-router-dom'

import { router } from './routes'

/** Mounts the application router. */
export function AppRouter() {
  return <RouterProvider router={router} />
}
