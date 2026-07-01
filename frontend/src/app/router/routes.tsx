import { createBrowserRouter } from 'react-router-dom'

import { RootLayout } from '@/app/layouts'
import { ProtectedRoute } from '@/features/auth'
import { CampaignDetailPage } from '@/pages/campaign-detail'
import { CampaignWarRoomPage } from '@/pages/campaign-war-room'
import { CampaignsPage } from '@/pages/campaigns'
import { DashboardPage } from '@/pages/dashboard'
import { LoginPage } from '@/pages/login'
import { NotFoundPage } from '@/pages/not-found'
import { SettingsPage } from '@/pages/settings'
import { UiKitPage } from '@/pages/ui-kit'

/**
 * Route tree.
 *
 * `/login` is public. Everything else sits behind <ProtectedRoute>, which
 * redirects to /login when unauthenticated. RootLayout renders the app frame
 * and the active route via <Outlet />.
 */
export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <RootLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'campaigns', element: <CampaignsPage /> },
          { path: 'campaigns/:campaignId', element: <CampaignDetailPage /> },
          {
            path: 'campaigns/:campaignId/war-room',
            element: <CampaignWarRoomPage />,
          },
          { path: 'settings', element: <SettingsPage /> },
          { path: 'ui-kit', element: <UiKitPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
])
