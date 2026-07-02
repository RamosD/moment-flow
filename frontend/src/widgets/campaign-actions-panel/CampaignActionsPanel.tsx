import { useState } from 'react'
import type { ReactNode } from 'react'

import type { CampaignAction } from '@/entities/campaign-action'
import {
  campaignActionPriorityLabel,
  campaignActionSourceLabel,
  campaignActionStatusLabel,
  campaignActionStatusVariant,
  campaignActionTypeLabel,
  relatedArtifactStatusLabel,
  relatedArtifactStatusVariant,
  useCampaignActions,
} from '@/entities/campaign-action'
import listStyles from '@/shared/styles/output-list.module.css'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Section,
} from '@/shared/ui'

import { CampaignActionLifecycleControls } from './CampaignActionLifecycleControls'
import styles from './CampaignActionsPanel.module.css'

interface CampaignActionsPanelProps {
  workspaceId: string | null
  campaignId: string | undefined
}

const PAGE_SIZE = 25

function formatDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
}

function metaLine(action: CampaignAction): string {
  return [
    campaignActionTypeLabel(action.action_type),
    `Priority: ${campaignActionPriorityLabel(action.priority)}`,
    `Source: ${campaignActionSourceLabel(action.source)}`,
    `Created: ${formatDateTime(action.created_at)}`,
  ].join(' · ')
}

function terminalDetails(action: CampaignAction): string[] {
  const details: string[] = []
  if (action.completed_at) {
    details.push(`Completed: ${formatDateTime(action.completed_at)}`)
  }
  if (action.cancelled_at) {
    details.push(`Cancelled: ${formatDateTime(action.cancelled_at)}`)
  }
  if (action.dismiss_reason) {
    details.push(`Dismiss reason: ${action.dismiss_reason}`)
  }
  return details
}

function relatedItems(action: CampaignAction) {
  return [
    ['Content pack request', action.related_content_pack_request],
    ['Content output', action.related_content_output],
    ['Report', action.related_report],
    ['Media kit', action.related_media_kit],
  ].filter((item): item is [string, string] => item[1] !== null)
}

function expectsRelatedArtifact(action: CampaignAction): boolean {
  return (
    action.action_type === 'content_pack' ||
    action.action_type === 'report_request' ||
    action.action_type === 'media_kit_request'
  )
}

function CampaignActionItem({
  action,
  workspaceId,
}: {
  action: CampaignAction
  workspaceId: string | null
}) {
  const details = terminalDetails(action)
  const related = relatedItems(action)

  return (
    <li className={`${listStyles.item} ${styles.item}`}>
      <div className={listStyles.itemMain}>
        <span className={listStyles.itemTitle}>{action.title}</span>
        <span className={listStyles.itemMeta}>{metaLine(action)}</span>
        {details.length > 0 && (
          <span className={styles.details}>{details.join(' · ')}</span>
        )}
        {related.length > 0 && (
          <span className={styles.relations}>
            {related.map(([label, id]) => (
              <span key={label} className={styles.relation} title={id}>
                {label}: {id}
              </span>
            ))}
          </span>
        )}
        {related.length === 0 && expectsRelatedArtifact(action) && (
          <span className={styles.relationMissing}>
            Related artifact unavailable or not linked.
          </span>
        )}
      </div>
      <div className={styles.itemAside}>
        <Badge variant={campaignActionStatusVariant(action.status)}>
          {campaignActionStatusLabel(action.status)}
        </Badge>
        {action.related_artifact_status && (
          <Badge
            variant={relatedArtifactStatusVariant(
              action.related_artifact_status.status,
            )}
          >
            {relatedArtifactStatusLabel(action.related_artifact_status)}
          </Badge>
        )}
        <CampaignActionLifecycleControls
          action={action}
          workspaceId={workspaceId}
        />
      </div>
    </li>
  )
}

/** Persistent CampaignActions for a campaign. No legacy artefact projection. */
function CampaignActionsPanelContent({
  workspaceId,
  campaignId,
}: CampaignActionsPanelProps) {
  const [page, setPage] = useState(1)

  const { data, isPending, isError, error, refetch } = useCampaignActions(
    workspaceId,
    campaignId,
    { page, page_size: PAGE_SIZE },
  )

  let body: ReactNode
  if (!workspaceId || !campaignId) {
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
  } else if (data.count === 0) {
    body = (
      <EmptyState
        title="No persistent actions yet"
        description="Only CampaignActions recorded in the new API appear here. Earlier artifacts remain available in their own panels."
      />
    )
  } else if (data.results.length === 0) {
    body = (
      <div className={styles.emptyPage}>
        <EmptyState
          title="No actions on this page"
          description={`This campaign still has ${data.count} persistent actions. Return to the first page to continue browsing.`}
        />
        <Button variant="secondary" size="sm" onClick={() => setPage(1)}>
          Return to first page
        </Button>
      </div>
    )
  } else {
    const totalPages = Math.max(1, Math.ceil(data.count / PAGE_SIZE))
    body = (
      <>
        <ul className={listStyles.list}>
          {data.results.map((action) => (
            <CampaignActionItem
              key={action.id}
              action={action}
              workspaceId={workspaceId}
            />
          ))}
        </ul>
        <div className={styles.pagination} aria-label="Campaign actions pages">
          <Button
            variant="secondary"
            size="sm"
            disabled={!data.previous}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </Button>
          <span className={styles.pageInfo}>
            Page {page} of {totalPages} · {data.count} actions
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={!data.next}
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </Button>
        </div>
      </>
    )
  }

  return (
    <Card padding="lg">
      <Section
        title="Campaign Actions"
        description="Persistent actions recorded for this campaign."
      >
        <div className={styles.body}>{body}</div>
      </Section>
    </Card>
  )
}

/** Reset panel-local pagination whenever its workspace/campaign scope changes. */
export function CampaignActionsPanel(props: CampaignActionsPanelProps) {
  const scope = `${props.workspaceId ?? 'none'}:${props.campaignId ?? 'none'}`
  return <CampaignActionsPanelContent key={scope} {...props} />
}
