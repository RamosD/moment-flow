import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useCampaigns, type CampaignStatus } from '@/entities/campaign'
import { useWorkspace } from '@/features/workspace-switching'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  WorkspaceRequiredState,
  type BadgeVariant,
} from '@/shared/ui'

import styles from './CampaignsPage.module.css'

const STATUS_VARIANT: Record<CampaignStatus, BadgeVariant> = {
  draft: 'neutral',
  scheduled: 'info',
  active: 'success',
  paused: 'warning',
  completed: 'primary',
  archived: 'neutral',
}

function statusVariant(status?: CampaignStatus): BadgeVariant {
  return status ? STATUS_VARIANT[status] : 'neutral'
}

/** Campaign list for the active workspace. */
export function CampaignsPage() {
  const { workspaceId } = useWorkspace()
  const { data: campaigns, isPending, isError, error, refetch } =
    useCampaigns(workspaceId)

  let body: ReactNode
  if (!workspaceId) {
    body = <WorkspaceRequiredState />
  } else if (isPending) {
    body = <LoadingState label="Loading campaigns…" />
  } else if (isError) {
    body = <ErrorState error={error} onRetry={() => void refetch()} />
  } else if (campaigns.length === 0) {
    body = (
      <EmptyState
        title="No campaigns yet"
        description="Campaigns created in the Backend Core will appear here."
      />
    )
  } else {
    body = (
      <ul className={styles.list}>
        {campaigns.map((campaign) => (
          <li key={campaign.id}>
            <Link to={`/campaigns/${campaign.id}`} className={styles.item}>
              <Card>
                <div className={styles.itemHead}>
                  <span className={styles.name}>{campaign.name}</span>
                  <Badge variant={statusVariant(campaign.status)}>
                    {campaign.status ?? 'unknown'}
                  </Badge>
                </div>
                {campaign.primary_goal && (
                  <p className={styles.meta}>{campaign.primary_goal}</p>
                )}
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <>
      <PageHeader
        title="Campaigns"
        description="Campaigns in the active workspace."
      />
      {body}
    </>
  )
}
