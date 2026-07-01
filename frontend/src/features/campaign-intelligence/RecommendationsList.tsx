import type { ReactNode } from 'react'

import type { CampaignRecommendation } from '@/entities/campaign'

import { RecommendationItem } from './RecommendationItem'
import styles from './intelligence.module.css'

/**
 * Recommended next steps. Honest empty message when none are available.
 *
 * `renderAction` is an optional slot the page uses to attach a per-recommendation
 * execution affordance. It receives the same `index` used elsewhere for the
 * defensive recommendation ref, so action state stays stable across renders.
 */
export function RecommendationsList({
  recommendations,
  renderAction,
}: {
  recommendations?: CampaignRecommendation[]
  renderAction?: (
    recommendation: CampaignRecommendation,
    index: number,
  ) => ReactNode
}) {
  if (!recommendations || recommendations.length === 0) {
    return <p className={styles.itemDesc}>No recommendations available yet.</p>
  }
  return (
    <ul className={styles.list}>
      {recommendations.map((recommendation, index) => (
        <RecommendationItem
          key={recommendation.id ?? index}
          recommendation={recommendation}
          action={renderAction?.(recommendation, index)}
        />
      ))}
    </ul>
  )
}
