import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useCampaign } from '@/entities/campaign'
import { CreateActionFromRecommendationButton } from '@/features/campaign-actions'
import {
  ExplanationsPanel,
  IntelligenceSummary,
  useCampaignIntelligence,
  WarningsPanel,
} from '@/features/campaign-intelligence'
import { useWorkspace } from '@/features/workspace-switching'
import { CampaignActionsPanel } from '@/widgets/campaign-actions-panel'
import { CampaignAssetsPanel } from '@/widgets/campaign-assets-panel'
import { CampaignHeader } from '@/widgets/campaign-header'
import { CampaignMediaKitsPanel } from '@/widgets/campaign-media-kits-panel'
import { CampaignMomentsPanel } from '@/widgets/campaign-moments-panel'
import { CampaignRecommendationsPanel } from '@/widgets/campaign-recommendations-panel'
import { CampaignReportsPanel } from '@/widgets/campaign-reports-panel'
import { CampaignScoreCard } from '@/widgets/campaign-score-card'
import {
  EmptyState,
  ErrorState,
  LoadingState,
  WorkspaceRequiredState,
} from '@/shared/ui'

import styles from './CampaignWarRoomPage.module.css'

/**
 * Campaign War Room MVP.
 *
 * Composes independent Backend Core data sources into a single dashboard:
 * campaign, intelligence, persistent CampaignActions and proprietary output
 * panels. The page stays useful when intelligence or CampaignActions fail;
 * sibling panels keep their own query/error boundaries. Never calls the
 * Intelligence Engine or Renderer directly.
 */
export function CampaignWarRoomPage() {
  const { campaignId } = useParams()
  const { workspaceId } = useWorkspace()

  const campaignQuery = useCampaign(workspaceId, campaignId)
  const intelligenceQuery = useCampaignIntelligence(workspaceId, campaignId)

  if (!workspaceId) {
    return <WorkspaceRequiredState />
  }

  if (campaignQuery.isError) {
    return (
      <ErrorState
        error={campaignQuery.error}
        onRetry={() => void campaignQuery.refetch()}
      />
    )
  }

  let intelligenceSection: ReactNode
  if (intelligenceQuery.isPending) {
    intelligenceSection = <LoadingState label="Analyzing campaign…" />
  } else if (intelligenceQuery.isError) {
    intelligenceSection = (
      <ErrorState
        error={intelligenceQuery.error}
        onRetry={() => void intelligenceQuery.refetch()}
      />
    )
  } else {
    const data = intelligenceQuery.data
    const result = data.result
    const hasSignal = Boolean(
      result?.summary ||
        result?.grade ||
        (result?.scores && Object.keys(result.scores).length > 0) ||
        (result?.moments && result.moments.length > 0) ||
        (result?.recommendations && result.recommendations.length > 0),
    )

    intelligenceSection = (
      <div className={styles.intelligence}>
        <IntelligenceSummary intelligence={data} />
        <WarningsPanel warnings={data.warnings} />
        {hasSignal ? (
          <>
            <CampaignScoreCard grade={result?.grade} scores={result?.scores} />
            <div className={styles.grid}>
              <CampaignMomentsPanel moments={result?.moments} />
              <CampaignRecommendationsPanel
                recommendations={result?.recommendations}
                renderAction={(recommendation, index) => (
                  <CreateActionFromRecommendationButton
                    workspaceId={workspaceId}
                    campaign={campaignQuery.data}
                    recommendation={recommendation}
                    index={index}
                  />
                )}
              />
            </div>
          </>
        ) : (
          <EmptyState
            title="Not enough data yet"
            description="There isn’t enough signal to analyze this campaign right now. Check back once there’s more activity."
          />
        )}
        <ExplanationsPanel explanations={data.explanations} />
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <nav className={styles.breadcrumb} aria-label="Breadcrumb">
        <Link to="/campaigns">Campaigns</Link>
        <span className={styles.sep}>/</span>
        {campaignId ? (
          <Link to={`/campaigns/${campaignId}`}>
            {campaignQuery.data?.name ?? 'Campaign'}
          </Link>
        ) : (
          <span>Campaign</span>
        )}
        <span className={styles.sep}>/</span>
        <span className={styles.current}>War Room</span>
      </nav>

      <CampaignHeader
        campaign={campaignQuery.data}
        isLoading={campaignQuery.isPending}
      />

      {intelligenceSection}

      <CampaignActionsPanel workspaceId={workspaceId} campaignId={campaignId} />

      <div className={styles.outputsGrid}>
        <CampaignAssetsPanel workspaceId={workspaceId} campaignId={campaignId} />
        <CampaignReportsPanel workspaceId={workspaceId} campaignId={campaignId} />
        <CampaignMediaKitsPanel
          workspaceId={workspaceId}
          campaignId={campaignId}
        />
      </div>
    </div>
  )
}
