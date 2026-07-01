import type { ReactNode } from 'react'

import type { CampaignRecommendation } from '@/entities/campaign'
import { RecommendationsList } from '@/features/campaign-intelligence'
import { Card, Section } from '@/shared/ui'

interface CampaignRecommendationsPanelProps {
  recommendations?: CampaignRecommendation[]
  /** Optional per-recommendation execution affordance, supplied by the page. */
  renderAction?: (
    recommendation: CampaignRecommendation,
    index: number,
  ) => ReactNode
}

/**
 * War Room panel listing recommended next steps. Display-only on its own; the
 * page may inject a Create-action affordance per recommendation via
 * `renderAction` without this widget knowing about the campaign-actions feature.
 */
export function CampaignRecommendationsPanel({
  recommendations,
  renderAction,
}: CampaignRecommendationsPanelProps) {
  return (
    <Card padding="lg">
      <Section title="Recommendations">
        <RecommendationsList
          recommendations={recommendations}
          renderAction={renderAction}
        />
      </Section>
    </Card>
  )
}
