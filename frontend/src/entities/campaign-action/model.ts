/**
 * Campaign Action — frontend model.
 *
 * IMPORTANT CONTRACT NOTE (see prompt_01 investigation): the Backend Core has
 * **no** dedicated "campaign action" / "task" entity, and recommendations are
 * recomputed on every `POST /campaigns/{id}/intelligence/` call (no
 * persistence). There is therefore nothing to invent here.
 *
 * What the Backend Core *does* expose are three real, campaign-scoped execution
 * endpoints that a recommendation can be turned into:
 *
 *   - content_pack       → POST /content-pack-requests/  (requires content_pack)
 *   - report_request     → POST /reports/                (requires report_type + title)
 *   - media_kit_request  → POST /media-kits/             (requires artist + title)
 *
 * A {@link CampaignAction} is consequently a **frontend projection** over the
 * artifact those endpoints create — not a backend record of its own. Action
 * types that have no real contract (manual_task, asset_request, mark_reviewed,
 * dismiss) are kept here only so the UI can render honest *disabled*
 * affordances. They are never persisted and never call a fake endpoint.
 */

import type { ISODateTimeString, Metadata, UUID } from '@/shared/types'

/** Every action type surfaced in the UI (supported + honest-unsupported). */
export type CampaignActionType =
  | 'content_pack'
  | 'report_request'
  | 'media_kit_request'
  | 'manual_task'
  | 'asset_request'
  | 'mark_reviewed'
  | 'dismiss'

/** Action types backed by a real Backend Core endpoint. */
export const SUPPORTED_CAMPAIGN_ACTION_TYPES = [
  'content_pack',
  'report_request',
  'media_kit_request',
] as const

export type SupportedCampaignActionType =
  (typeof SUPPORTED_CAMPAIGN_ACTION_TYPES)[number]

/** Underlying Backend Core artifact a (supported) action projects from. */
export type CampaignActionArtifactKind =
  | 'content_pack_request'
  | 'report'
  | 'media_kit'

/** Where the action originated. Inferred from artifact metadata when listing. */
export type CampaignActionSource = 'recommendation' | 'manual'

/**
 * Normalized status vocabulary for badges. The three backing artifacts use
 * different status enums; {@link normalizeActionStatus} maps them to this
 * shared set. `dismissed` is reserved for forward-compatibility and is
 * currently unreachable — the Backend Core has no dismiss contract.
 */
export type CampaignActionStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'dismissed'
  | 'unknown'

/** A campaign action as projected from a real Backend Core artifact. */
export interface CampaignAction {
  /** Id of the underlying artifact (content-pack-request / report / media-kit). */
  id: UUID
  type: SupportedCampaignActionType
  artifactKind: CampaignActionArtifactKind
  campaignId: UUID | null
  title: string
  status: CampaignActionStatus
  /** Native backend status token, preserved for badge/debug fidelity. */
  rawStatus: string | null
  source: CampaignActionSource
  /**
   * Best-effort priority read from the artifact `metadata` bag
   * (`action_priority`). The backing endpoints have no priority column — this
   * is a frontend convention written at creation time, not a backend field.
   */
  priority: string | null
  /**
   * Best-effort recommendation linkage read from the artifact `metadata` bag.
   * This is NOT a persisted relational contract — the Backend Core has no
   * recommendation foreign key (see {@link deriveRecommendationRef}).
   */
  recommendationRef: string | null
  createdAt: ISODateTimeString
  updatedAt: ISODateTimeString | null
  metadata: Metadata | null
}

/** Declares whether/how each action type is backed by the Backend Core. */
export interface CampaignActionCapability {
  type: CampaignActionType
  supported: boolean
  /** Backend Core endpoint used when supported; `null` otherwise. */
  endpoint: string | null
  /** Whether the artifact can be updated after creation (PATCH). */
  updatable: boolean
  /** Honest, user-facing explanation when unsupported; `null` when supported. */
  reason: string | null
}

/**
 * Single source of truth for what the UI may offer. Drives disabled states and
 * honest copy — keeps any "create action" surface aligned to the real contract.
 */
export const CAMPAIGN_ACTION_CAPABILITIES: Record<
  CampaignActionType,
  CampaignActionCapability
> = {
  content_pack: {
    type: 'content_pack',
    supported: true,
    endpoint: '/content-pack-requests/',
    updatable: false,
    reason: null,
  },
  report_request: {
    type: 'report_request',
    supported: true,
    endpoint: '/reports/',
    updatable: true,
    reason: null,
  },
  media_kit_request: {
    type: 'media_kit_request',
    supported: true,
    endpoint: '/media-kits/',
    updatable: true,
    reason: null,
  },
  manual_task: {
    type: 'manual_task',
    supported: false,
    endpoint: null,
    updatable: false,
    reason: 'Backend Core exposes no task/action entity yet.',
  },
  asset_request: {
    type: 'asset_request',
    supported: false,
    endpoint: null,
    updatable: false,
    reason: 'Backend Core exposes no asset-request endpoint yet.',
  },
  mark_reviewed: {
    type: 'mark_reviewed',
    supported: false,
    endpoint: null,
    updatable: false,
    reason:
      'Recommendations are recomputed, not persisted; review state cannot be stored.',
  },
  dismiss: {
    type: 'dismiss',
    supported: false,
    endpoint: null,
    updatable: false,
    reason:
      'Recommendations are recomputed, not persisted; dismissal cannot be stored.',
  },
}

export function isSupportedCampaignActionType(
  type: CampaignActionType,
): type is SupportedCampaignActionType {
  return CAMPAIGN_ACTION_CAPABILITIES[type].supported
}

// ---------------------------------------------------------------------------
// Create / update payloads — aligned exactly to each real endpoint's writable
// fields. Each supported type has DIFFERENT required fields, so the create
// input is a discriminated union rather than one flat shape.
// ---------------------------------------------------------------------------

interface BaseCreateCampaignActionInput {
  campaignId: UUID
  /** Optional recommendation linkage; stored (best-effort) in artifact metadata. */
  recommendationRef?: string | null
  /** Defaults to `recommendation` when a ref is present, else `manual`. */
  source?: CampaignActionSource
  /** Extra metadata merged into the artifact's metadata bag. */
  metadata?: Metadata
}

/** `POST /reports/` — requires `report_type` (defaulted) + `title`. */
export interface CreateReportActionInput extends BaseCreateCampaignActionInput {
  type: 'report_request'
  title: string
  /** Backend `report_type` choice. Defaults to `campaign_report`. */
  reportType?: string
  artistId?: UUID | null
  trackId?: UUID | null
}

/** `POST /media-kits/` — requires `artist` + `title`. */
export interface CreateMediaKitActionInput extends BaseCreateCampaignActionInput {
  type: 'media_kit_request'
  title: string
  /** Required by the Backend Core; derive from `campaign.artist`. */
  artistId: UUID
  trackId?: UUID | null
}

/** `POST /content-pack-requests/` — requires `campaign` + `content_pack`. */
export interface CreateContentPackActionInput
  extends BaseCreateCampaignActionInput {
  type: 'content_pack'
  /** Catalogue content-pack id chosen by the user (no native title field). */
  contentPackId: UUID
  /** Display title (projection only; persisted into metadata, not a column). */
  title?: string
  artistId?: UUID | null
  trackId?: UUID | null
}

export type CreateCampaignActionInput =
  | CreateReportActionInput
  | CreateMediaKitActionInput
  | CreateContentPackActionInput

/**
 * Update payload. Only `report_request` and `media_kit_request` support PATCH;
 * `content_pack` (content-pack-request) has no update route and a read-only
 * status — see {@link CAMPAIGN_ACTION_CAPABILITIES}.
 */
export interface UpdateCampaignActionInput {
  type: SupportedCampaignActionType
  id: UUID
  /** Native backend status token for the artifact (e.g. report `archived`). */
  status?: string
  metadata?: Metadata
}
