import { useNavigate } from 'react-router-dom'

import { Button, Card, PageHeader } from '@/shared/ui'

/** Placeholder home/dashboard. Real content arrives in later phases. */
export function DashboardPage() {
  const navigate = useNavigate()
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Welcome to MomentFlow. Start from your campaigns."
        actions={
          <Button onClick={() => navigate('/campaigns')}>View campaigns</Button>
        }
      />
      <Card>
        <p>Your overview will appear here in a later phase.</p>
      </Card>
    </>
  )
}
