import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { useCampaign } from '@/entities/campaign'
import { useWorkspace } from '@/features/workspace-switching'
import {
  Button,
  Card,
  ErrorState,
  LoadingState,
  PageHeader,
  WorkspaceRequiredState,
} from '@/shared/ui'

import styles from './CampaignDetailPage.module.css'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className={styles.term}>{label}</dt>
      <dd className={styles.value}>{children}</dd>
    </>
  )
}

/** Simple campaign detail with navigation into the War Room. */
export function CampaignDetailPage() {
  const { campaignId } = useParams()
  const navigate = useNavigate()
  const { workspaceId } = useWorkspace()
  const { data: campaign, isPending, isError, error, refetch } = useCampaign(
    workspaceId,
    campaignId,
  )

  let body: ReactNode
  if (!workspaceId) {
    body = <WorkspaceRequiredState />
  } else if (isPending) {
    body = <LoadingState label="Loading campaign…" />
  } else if (isError) {
    body = <ErrorState error={error} onRetry={() => void refetch()} />
  } else {
    body = (
      <Card padding="lg">
        <dl className={styles.details}>
          <Field label="Status">{campaign.status ?? '—'}</Field>
          <Field label="Type">{campaign.campaign_type ?? '—'}</Field>
          <Field label="Primary goal">{campaign.primary_goal || '—'}</Field>
          <Field label="Start date">{campaign.start_date ?? '—'}</Field>
          <Field label="End date">{campaign.end_date ?? '—'}</Field>
        </dl>
        {campaign.description && (
          <p className={styles.description}>{campaign.description}</p>
        )}
      </Card>
    )
  }

  return (
    <>
      <PageHeader
        title={campaign?.name ?? 'Campaign'}
        actions={
          <Button onClick={() => navigate('war-room')}>Open War Room</Button>
        }
      />
      {body}
    </>
  )
}
