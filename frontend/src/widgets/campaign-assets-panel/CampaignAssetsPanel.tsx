import type { ReactNode } from 'react'

import { useCampaignContentOutputs } from '@/entities/content-output'
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

interface CampaignAssetsPanelProps {
  workspaceId: string | null
  campaignId: string | undefined
}

/**
 * Content outputs for the campaign, from the Backend Core
 * (`GET /content-outputs/?campaign=…`). Read-only: the Content Renderer is
 * never called directly and no asset generation happens here.
 */
export function CampaignAssetsPanel({
  workspaceId,
  campaignId,
}: CampaignAssetsPanelProps) {
  const { data, isPending, isError, error, refetch } =
    useCampaignContentOutputs(workspaceId, campaignId)

  let body: ReactNode
  if (isPending) {
    body = <LoadingState label="Loading content outputs…" />
  } else if (isError) {
    body = <ErrorState error={error} onRetry={() => void refetch()} />
  } else if (data.length === 0) {
    body = (
      <EmptyState
        title="No content outputs yet"
        description="Generated assets for this campaign will appear here."
      />
    )
  } else {
    body = (
      <ul className={listStyles.list}>
        {data.map((output) => (
          <li key={output.id} className={listStyles.item}>
            <div className={listStyles.itemMain}>
              <span className={listStyles.itemTitle}>
                {output.title || output.output_type}
              </span>
              <span className={listStyles.itemMeta}>
                {[output.output_type, output.format].filter(Boolean).join(' · ')}
              </span>
            </div>
            <Badge variant={statusToBadgeVariant(output.status)}>
              {output.status ?? 'unknown'}
            </Badge>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <Card padding="lg">
      <Section title="Content outputs">{body}</Section>
    </Card>
  )
}
