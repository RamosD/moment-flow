import {
  EmptyState,
  ErrorState,
  LoadingState,
  Section,
  WorkspaceRequiredState,
} from '@/shared/ui'

import { ExplanationsPanel } from './ExplanationsPanel'
import { GradeBadge } from './GradeBadge'
import { IntelligenceSummary } from './IntelligenceSummary'
import { MomentsList } from './MomentsList'
import { RecommendationsList } from './RecommendationsList'
import { ScoreGrid } from './ScoreGrid'
import { WarningsPanel } from './WarningsPanel'
import { useCampaignIntelligence } from './useCampaignIntelligence'
import styles from './intelligence.module.css'

interface CampaignIntelligencePanelProps {
  /** Passed in by the page (keeps this feature decoupled from workspace feature). */
  workspaceId: string | null
  campaignId: string | undefined
}

/**
 * Orchestrates campaign intelligence: loads via the Backend Core, handles every
 * state, and composes the presentational panels. The `ErrorState` derives copy
 * for 401/403/404/422/502/503/network, so upstream/engine outages (502/503)
 * get their own "Service unavailable" UI for free.
 */
export function CampaignIntelligencePanel({
  workspaceId,
  campaignId,
}: CampaignIntelligencePanelProps) {
  const { data, isPending, isError, error, refetch } = useCampaignIntelligence(
    workspaceId,
    campaignId,
  )

  if (!workspaceId) {
    return <WorkspaceRequiredState />
  }
  if (isPending) {
    return <LoadingState label="Analyzing campaign…" />
  }
  if (isError) {
    return <ErrorState error={error} onRetry={() => void refetch()} />
  }

  const result = data.result
  const hasSignal = Boolean(
    result?.summary ||
      result?.grade ||
      (result?.scores && Object.keys(result.scores).length > 0) ||
      (result?.moments && result.moments.length > 0) ||
      (result?.recommendations && result.recommendations.length > 0),
  )

  if (!hasSignal) {
    return (
      <div className={styles.panel}>
        <IntelligenceSummary intelligence={data} />
        <WarningsPanel warnings={data.warnings} />
        <EmptyState
          title="Not enough data yet"
          description="There isn’t enough signal to analyze this campaign right now. Check back once there’s more activity."
        />
        <ExplanationsPanel explanations={data.explanations} />
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <IntelligenceSummary intelligence={data} />

      <WarningsPanel warnings={data.warnings} />

      <Section title="Grade & scores">
        <div className={styles.gradeRow}>
          <span className={styles.gradeLabel}>Overall grade</span>
          <GradeBadge grade={result?.grade} />
        </div>
        <ScoreGrid scores={result?.scores} />
      </Section>

      <Section title="Moments">
        <MomentsList moments={result?.moments} />
      </Section>

      <Section title="Recommendations">
        <RecommendationsList recommendations={result?.recommendations} />
      </Section>

      <ExplanationsPanel explanations={data.explanations} />
    </div>
  )
}
