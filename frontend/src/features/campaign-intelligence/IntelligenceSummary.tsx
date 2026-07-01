import type { CampaignIntelligence } from '@/entities/campaign'
import { Badge } from '@/shared/ui'

import styles from './intelligence.module.css'

/**
 * Headline of the intelligence result: the source (live engine vs dry run),
 * engine identity, the summary text, and when it was generated.
 */
export function IntelligenceSummary({
  intelligence,
}: {
  intelligence: CampaignIntelligence
}) {
  const { result, source, engine, engine_version, generated_at } = intelligence

  return (
    <div className={styles.summary}>
      <div className={styles.summaryHead}>
        {source === 'dry_run' ? (
          <Badge variant="info">Dry run</Badge>
        ) : (
          <Badge variant="success">Live engine</Badge>
        )}
        {engine && (
          <span className={styles.meta}>
            {engine}
            {engine_version ? ` · v${engine_version}` : ''}
          </span>
        )}
      </div>
      {result?.summary ? (
        <p className={styles.summaryText}>{result.summary}</p>
      ) : (
        <p className={styles.itemDesc}>No summary provided for this campaign.</p>
      )}
      {generated_at && (
        <span className={styles.meta}>Generated at {generated_at}</span>
      )}
    </div>
  )
}
