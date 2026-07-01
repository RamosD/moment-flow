import type { ReactNode } from 'react'

import { useCampaignReports } from '@/entities/report'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Section,
  statusToBadgeVariant,
} from '@/shared/ui'
import listStyles from '@/shared/styles/output-list.module.css'

interface CampaignReportsPanelProps {
  workspaceId: string | null
  campaignId: string | undefined
}

function humanize(value: string): string {
  return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Reports for the campaign, from the Backend Core (`GET /reports/?campaign=…`).
 * Read-only — no generation, no direct Renderer calls.
 */
export function CampaignReportsPanel({
  workspaceId,
  campaignId,
}: CampaignReportsPanelProps) {
  const { data, isPending, isError, error, refetch } = useCampaignReports(
    workspaceId,
    campaignId,
  )

  let body: ReactNode
  if (isPending) {
    body = <LoadingState label="Loading reports…" />
  } else if (isError) {
    body = <ErrorState error={error} onRetry={() => void refetch()} />
  } else if (data.length === 0) {
    body = (
      <EmptyState
        title="No reports yet"
        description="Reports generated for this campaign will appear here."
      />
    )
  } else {
    body = (
      <ul className={listStyles.list}>
        {data.map((report) => (
          <li key={report.id} className={listStyles.item}>
            <div className={listStyles.itemMain}>
              <span className={listStyles.itemTitle}>{report.title}</span>
              <span className={listStyles.itemMeta}>
                {humanize(report.report_type)}
              </span>
            </div>
            <Badge variant={statusToBadgeVariant(report.status)}>
              {report.status ?? 'unknown'}
            </Badge>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <Card padding="lg">
      <Section title="Reports">{body}</Section>
    </Card>
  )
}
