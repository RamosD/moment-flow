import type { CampaignScores } from '@/entities/campaign'
import { GradeBadge, ScoreGrid } from '@/features/campaign-intelligence'
import { Card, Section } from '@/shared/ui'

import styles from './CampaignScoreCard.module.css'

interface CampaignScoreCardProps {
  grade?: string | null
  scores?: CampaignScores
}

/**
 * Grade + scores card. The grade doubles as the priority signal (the contract
 * has no explicit priority field). Scores are display-only — never computed here.
 */
export function CampaignScoreCard({ grade, scores }: CampaignScoreCardProps) {
  return (
    <Card padding="lg">
      <Section title="Grade & scores">
        <div className={styles.gradeRow}>
          <span className={styles.gradeLabel}>Overall grade</span>
          <GradeBadge grade={grade} />
        </div>
        <ScoreGrid scores={scores} />
      </Section>
    </Card>
  )
}
