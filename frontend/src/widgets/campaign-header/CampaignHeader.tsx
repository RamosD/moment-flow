import type { Campaign, CampaignStatus } from '@/entities/campaign'
import { Badge, Skeleton, type BadgeVariant } from '@/shared/ui'

import styles from './CampaignHeader.module.css'

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

function humanize(value: string): string {
  return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

interface CampaignHeaderProps {
  campaign?: Campaign
  isLoading?: boolean
}

/** War Room header: campaign name, status and key metadata. */
export function CampaignHeader({ campaign, isLoading }: CampaignHeaderProps) {
  if (isLoading) {
    return (
      <div className={styles.loading}>
        <Skeleton width="40%" height="2rem" />
        <Skeleton width="25%" height="1rem" />
      </div>
    )
  }
  if (!campaign) return null

  const dateRange = [campaign.start_date, campaign.end_date]
    .filter(Boolean)
    .join(' → ')

  return (
    <header className={styles.header}>
      <div className={styles.titleRow}>
        <h1 className={styles.title}>{campaign.name}</h1>
        <Badge variant={statusVariant(campaign.status)}>
          {campaign.status ?? 'unknown'}
        </Badge>
      </div>
      <div className={styles.meta}>
        {campaign.campaign_type && <span>{humanize(campaign.campaign_type)}</span>}
        {campaign.primary_goal && <span>· {campaign.primary_goal}</span>}
        {dateRange && <span>· {dateRange}</span>}
      </div>
    </header>
  )
}
