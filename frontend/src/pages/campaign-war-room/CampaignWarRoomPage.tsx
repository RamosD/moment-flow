import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useCampaign } from '@/entities/campaign'
import { useCampaignActions } from '@/entities/campaign-action'
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
 * Composes two real data sources from the Backend Core — the campaign (header)
 * and its intelligence — into a single dashboard. Assets/reports are honest
 * placeholders (FE-012). The page stays useful even when intelligence fails,
 * has warnings, or returns insufficient data: the header and the assets/reports
 * areas always render. Never calls the Intelligence Engine or Renderer directly.
 */
export function CampaignWarRoomPage() {
  const { campaignId } = useParams()
  const { workspaceId } = useWorkspace()

  const campaignQuery = useCampaign(workspaceId, campaignId)
  const intelligenceQuery = useCampaignIntelligence(workspaceId, campaignId)
  // Drives recommendation execution state (CA-009) and feeds the actions panel.
  // Shares its cache key with the panel's own query, so this is a single fetch.
  const actionsQuery = useCampaignActions(workspaceId, campaignId)

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
                    actions={actionsQuery.data}
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
