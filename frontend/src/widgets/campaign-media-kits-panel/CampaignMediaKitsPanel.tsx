import type { ReactNode } from 'react'

import type { MediaKit } from '@/entities/media-kit'
import { useCampaignMediaKits } from '@/entities/media-kit'
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

interface CampaignMediaKitsPanelProps {
  workspaceId: string | null
  campaignId: string | undefined
}

/**
 * MediaKit has no dedicated `failed` status (STG-PRE-007) — a failed
 * generation is only recorded in `metadata.generation_status`/`error`, so a
 * failed kit would otherwise still show as "draft" and look like it's simply
 * pending. Surface it the same way the CampaignAction API already does.
 */
function mediaKitDisplayStatus(kit: MediaKit): string {
  if (kit.metadata?.generation_status === 'failed') return 'failed'
  return kit.status ?? 'unknown'
}

function mediaKitFailureMessage(kit: MediaKit): string | undefined {
  if (kit.metadata?.generation_status !== 'failed') return undefined
  const error = kit.metadata.error
  return typeof error === 'string' && error ? error : undefined
}

/**
 * Media kits for the campaign, from the Backend Core
 * (`GET /media-kits/?campaign=…`). Read-only — no generation, no direct
 * Renderer calls.
 */
export function CampaignMediaKitsPanel({
  workspaceId,
  campaignId,
}: CampaignMediaKitsPanelProps) {
  const { data, isPending, isError, error, refetch } = useCampaignMediaKits(
    workspaceId,
    campaignId,
  )

  let body: ReactNode
  if (isPending) {
    body = <LoadingState label="Loading media kits…" />
  } else if (isError) {
    body = <ErrorState error={error} onRetry={() => void refetch()} />
  } else if (data.length === 0) {
    body = (
      <EmptyState
        title="No media kits yet"
        description="Media kits created for this campaign will appear here."
      />
    )
  } else {
    body = (
      <ul className={listStyles.list}>
        {data.map((kit) => {
          const itemCount = kit.items?.length ?? 0
          const displayStatus = mediaKitDisplayStatus(kit)
          const failureMessage = mediaKitFailureMessage(kit)
          return (
            <li key={kit.id} className={listStyles.item}>
              <div className={listStyles.itemMain}>
                <span className={listStyles.itemTitle}>{kit.title}</span>
                <span className={listStyles.itemMeta}>
                  {itemCount} {itemCount === 1 ? 'item' : 'items'}
                </span>
                {failureMessage && (
                  <span className={listStyles.itemMeta} role="alert">
                    {failureMessage}
                  </span>
                )}
              </div>
              <Badge variant={statusToBadgeVariant(displayStatus)}>
                {displayStatus}
              </Badge>
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <Card padding="lg">
      <Section title="Media kits">{body}</Section>
    </Card>
  )
}
