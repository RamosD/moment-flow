/**
 * Campaign Intelligence types — the War Room core.
 *
 * Mirrors `CampaignIntelligenceResponse` / `CampaignIntelligenceResult` in the
 * Backend Core schema. IMPORTANT CONTRACT NOTE: in the OpenAPI schema,
 * `result.analysis` and `result.scores` are free-form objects, and
 * `result.moments` / `result.recommendations` are **untyped arrays**
 * (`items: {}`). The interfaces below are therefore best-effort: every
 * field is optional and an index signature allows unknown keys. Do not treat
 * these shapes as guaranteed — render defensively. Tighten them once the engine
 * contract is stabilized (see FE-PDEC-005).
 */

import type { Metadata } from '@/shared/types'

/** `source` discriminates a real engine call from a dry run. */
export type IntelligenceSource = 'engine' | 'dry_run'

/** `result.analysis` — free-form analysis bag. */
export type CampaignAnalysis = Record<string, unknown>

/** `result.scores` — free-form scores bag (metric → value). */
export type CampaignScores = Record<string, unknown>

/** A detected moment/signal. Best-effort shape; fields are not guaranteed. */
export interface CampaignMoment {
  id?: string
  type?: string
  title?: string
  label?: string
  description?: string
  priority?: string | number
  score?: number
  detected_at?: string
  [key: string]: unknown
}

/** A recommended next action. Best-effort shape; fields are not guaranteed. */
export interface CampaignRecommendation {
  id?: string
  type?: string
  title?: string
  description?: string
  priority?: string | number
  action?: string
  [key: string]: unknown
}

/** Free-form entries used by `explanations` / `warnings`. */
export type IntelligenceNote = Record<string, unknown>

/** The engine's `result` block. */
export interface CampaignIntelligenceResult {
  analysis?: CampaignAnalysis
  scores?: CampaignScores
  grade?: string | null
  moments?: CampaignMoment[]
  recommendations?: CampaignRecommendation[]
  summary?: string
}

/** Full intelligence response from `POST /campaigns/{id}/intelligence/`. */
export interface CampaignIntelligence {
  status: string
  source: IntelligenceSource
  engine: string
  engine_version: string
  request_id: string
  workspace_id: string
  campaign_id: string
  result: CampaignIntelligenceResult
  generated_at: string
  // Optional in the contract:
  explanations?: IntelligenceNote[]
  warnings?: IntelligenceNote[]
  metadata?: Metadata
}

/** Alias matching the Backend Core schema name. */
export type CampaignIntelligenceResponse = CampaignIntelligence
