import type { CampaignMoment } from '@/entities/campaign'
import { MomentsList } from '@/features/campaign-intelligence'
import { Card, Section } from '@/shared/ui'

interface CampaignMomentsPanelProps {
  moments?: CampaignMoment[]
}

/** War Room panel listing detected moments/signals. */
export function CampaignMomentsPanel({ moments }: CampaignMomentsPanelProps) {
  return (
    <Card padding="lg">
      <Section title="Moments">
        <MomentsList moments={moments} />
      </Section>
    </Card>
  )
}
