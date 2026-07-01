import type { ReactNode } from 'react'

import {
  campaignActionStatusLabel,
  campaignActionStatusVariant,
  campaignActionTypeLabel,
  useCampaignActions,
} from '@/entities/campaign-action'
import type { CampaignAction } from '@/entities/campaign-action'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Section,
} from '@/shared/ui'
import listStyles from '@/shared/styles/output-list.module.css'

import styles from './CampaignActionsPanel.module.css'

interface CampaignActionsPanelProps {
  workspaceId: string | null
  campaignId: string | undefined
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
}

function metaLine(action: CampaignAction): string {
  const parts = [campaignActionTypeLabel(action.type)]
  // Source doubles as the recommendation relation: "From recommendation" is set
  // exactly when a (best-effort) recommendation_ref is present in metadata.
  parts.push(action.source === 'recommendation' ? 'From recommendation' : 'Manual')
  if (action.priority) parts.push(`Priority: ${action.priority}`)
  parts.push(formatDate(action.createdAt))
  return parts.join(' · ')
}

/**
 * War Room panel of operational actions for the campaign (CA-008).
 *
 * "Campaign actions" is a frontend *projection* — the Backend Core has no
 * campaign-actions endpoint, so this aggregates the three real execution
 * artifacts (content-pack requests, reports, media kits) filtered by campaign.
 * Read-only; creation happens via the per-recommendation Create-action flow.
 */
export function CampaignActionsPanel({
  workspaceId,
  campaignId,
}: CampaignActionsPanelProps) {
  const { data, isPending, isError, error, refetch } = useCampaignActions(
    workspaceId,
    campaignId,
  )

  let body: ReactNode
  if (!workspaceId || !campaignId) {
    // The query is disabled without these, so it never leaves the pending
    // state — surface an honest message instead of a perpetual spinner.
    body = (
      <EmptyState
        title="No workspace selected"
        description="Select a workspace to see campaign actions."
      />
    )
  } else if (isPending) {
    body = <LoadingState label="Loading actions…" />
  } else if (isError) {
    body = <ErrorState error={error} onRetry={() => void refetch()} />
  } else if (data.length === 0) {
    body = (
      <EmptyState
        title="No actions yet"
        description="Convert a recommendation into an action to see it tracked here."
      />
    )
  } else {
    body = (
      <ul className={listStyles.list}>
        {data.map((action) => (
          <li key={action.id} className={listStyles.item}>
            <div className={listStyles.itemMain}>
              <span className={listStyles.itemTitle}>{action.title}</span>
              <span className={listStyles.itemMeta}>{metaLine(action)}</span>
            </div>
            <Badge variant={campaignActionStatusVariant(action.status)}>
              {campaignActionStatusLabel(action.status)}
            </Badge>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <Card padding="lg">
      <Section
        title="Campaign Actions"
        description="Operational artifacts created from this campaign."
      >
        <div className={styles.body}>{body}</div>
      </Section>
    </Card>
  )
}
