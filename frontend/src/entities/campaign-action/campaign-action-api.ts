/**
 * Campaign Actions data layer — Backend Core only.
 *
 * There is no `campaign-actions` endpoint. This module *projects* a unified
 * {@link CampaignAction} over three real, campaign-scoped endpoints and
 * dispatches creation/update to the right one:
 *
 *   content_pack       GET/POST  /content-pack-requests/   (no PATCH)
 *   report_request     GET/POST/PATCH  /reports/
 *   media_kit_request  GET/POST/PATCH  /media-kits/
 *
 * Recommendation linkage is written (best-effort) into the artifact `metadata`
 * bag (`recommendation_ref`, `action_source`, `action_title`) because the
 * Backend Core has no recommendation foreign key. This is a frontend
 * convention, not a relational contract.
 *
 * The Intelligence Engine and Content Renderer are never called directly, and
 * `X-Internal-Token` is never sent (the shared client forbids it).
 */

import { apiClient } from '@/shared/api'
import type {
  ISODateTimeString,
  Metadata,
  PaginatedResponse,
  UUID,
} from '@/shared/types'

import { normalizeActionStatus } from './helpers'
import type {
  CampaignAction,
  CampaignActionSource,
  CreateCampaignActionInput,
  UpdateCampaignActionInput,
} from './model'

const DEFAULT_REPORT_TYPE = 'campaign_report'
const PAGE_SIZE = 50

// --- Minimal raw shapes (only the fields we project). Declared locally to keep
// the entity decoupled from the content-output / report / media-kit entities. --

interface RawContentPackRequest {
  id: UUID
  campaign: UUID | null
  status?: string | null
  metadata?: Metadata | null
  created_at: ISODateTimeString
  updated_at?: ISODateTimeString | null
}

interface RawReport {
  id: UUID
  campaign?: UUID | null
  title?: string
  status?: string | null
  metadata?: Metadata | null
  created_at: ISODateTimeString
  updated_at?: ISODateTimeString | null
}

interface RawMediaKit {
  id: UUID
  campaign?: UUID | null
  title?: string
  status?: string | null
  metadata?: Metadata | null
  created_at: ISODateTimeString
  updated_at?: ISODateTimeString | null
}

// --------------------------- metadata helpers -----------------------------

function readMetaString(
  metadata: Metadata | null | undefined,
  key: string,
): string | null {
  if (!metadata) return null
  const value = (metadata as Record<string, unknown>)[key]
  return typeof value === 'string' && value.trim() ? value : null
}

function readSource(
  metadata: Metadata | null | undefined,
  hasRef: boolean,
): CampaignActionSource {
  const value = readMetaString(metadata, 'action_source')
  if (value === 'recommendation' || value === 'manual') return value
  return hasRef ? 'recommendation' : 'manual'
}

/** Merge recommendation/source/title hints into the outgoing metadata bag. */
function buildMetadata(
  input: CreateCampaignActionInput,
  title: string | undefined,
): Metadata | undefined {
  const meta: Record<string, unknown> = { ...(input.metadata ?? {}) }
  if (input.recommendationRef) meta.recommendation_ref = input.recommendationRef
  meta.action_source =
    input.source ?? (input.recommendationRef ? 'recommendation' : 'manual')
  if (title) meta.action_title = title
  return Object.keys(meta).length > 0 ? meta : undefined
}

// ----------------------------- projections --------------------------------

function projectContentPackRequest(raw: RawContentPackRequest): CampaignAction {
  const recommendationRef = readMetaString(raw.metadata, 'recommendation_ref')
  return {
    id: raw.id,
    type: 'content_pack',
    artifactKind: 'content_pack_request',
    campaignId: raw.campaign ?? null,
    title: readMetaString(raw.metadata, 'action_title') ?? 'Content pack',
    status: normalizeActionStatus(raw.status),
    rawStatus: raw.status ?? null,
    source: readSource(raw.metadata, !!recommendationRef),
    priority: readMetaString(raw.metadata, 'action_priority'),
    recommendationRef,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at ?? null,
    metadata: raw.metadata ?? null,
  }
}

function projectReport(raw: RawReport): CampaignAction {
  const recommendationRef = readMetaString(raw.metadata, 'recommendation_ref')
  return {
    id: raw.id,
    type: 'report_request',
    artifactKind: 'report',
    campaignId: raw.campaign ?? null,
    title:
      (raw.title && raw.title.trim()) ||
      readMetaString(raw.metadata, 'action_title') ||
      'Report',
    status: normalizeActionStatus(raw.status),
    rawStatus: raw.status ?? null,
    source: readSource(raw.metadata, !!recommendationRef),
    priority: readMetaString(raw.metadata, 'action_priority'),
    recommendationRef,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at ?? null,
    metadata: raw.metadata ?? null,
  }
}

function projectMediaKit(raw: RawMediaKit): CampaignAction {
  const recommendationRef = readMetaString(raw.metadata, 'recommendation_ref')
  return {
    id: raw.id,
    type: 'media_kit_request',
    artifactKind: 'media_kit',
    campaignId: raw.campaign ?? null,
    title:
      (raw.title && raw.title.trim()) ||
      readMetaString(raw.metadata, 'action_title') ||
      'Media kit',
    status: normalizeActionStatus(raw.status),
    rawStatus: raw.status ?? null,
    source: readSource(raw.metadata, !!recommendationRef),
    priority: readMetaString(raw.metadata, 'action_priority'),
    recommendationRef,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at ?? null,
    metadata: raw.metadata ?? null,
  }
}

function byCreatedAtDesc(a: CampaignAction, b: CampaignAction): number {
  return a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0
}

// ------------------------------- list -------------------------------------

/**
 * Aggregate campaign actions for a campaign by reading the three real
 * endpoints in parallel and projecting each into {@link CampaignAction}.
 *
 * Resilient by design: a single endpoint failing (e.g. a 403 on one resource)
 * does not blank the whole panel — its results are skipped. Only when *every*
 * endpoint fails is the first error rethrown so the query surfaces an error.
 */
export async function fetchCampaignActions(
  campaignId: string,
): Promise<CampaignAction[]> {
  const params = { campaign: campaignId, page_size: PAGE_SIZE }
  const settled = await Promise.allSettled([
    apiClient.get<PaginatedResponse<RawContentPackRequest>>(
      '/content-pack-requests/',
      { params },
    ),
    apiClient.get<PaginatedResponse<RawReport>>('/reports/', { params }),
    apiClient.get<PaginatedResponse<RawMediaKit>>('/media-kits/', { params }),
  ])

  const actions: CampaignAction[] = []
  let anyFulfilled = false

  if (settled[0].status === 'fulfilled') {
    anyFulfilled = true
    for (const item of settled[0].value.results) {
      actions.push(projectContentPackRequest(item))
    }
  }
  if (settled[1].status === 'fulfilled') {
    anyFulfilled = true
    for (const item of settled[1].value.results) {
      actions.push(projectReport(item))
    }
  }
  if (settled[2].status === 'fulfilled') {
    anyFulfilled = true
    for (const item of settled[2].value.results) {
      actions.push(projectMediaKit(item))
    }
  }

  if (!anyFulfilled) {
    const rejected = settled.find(
      (r): r is PromiseRejectedResult => r.status === 'rejected',
    )
    throw rejected
      ? rejected.reason
      : new Error('Failed to load campaign actions.')
  }

  return actions.sort(byCreatedAtDesc)
}

// ------------------------------ create ------------------------------------

/** Dispatch creation to the correct real endpoint and project the result. */
export async function createCampaignAction(
  input: CreateCampaignActionInput,
): Promise<CampaignAction> {
  switch (input.type) {
    case 'report_request': {
      const payload: Record<string, unknown> = {
        campaign: input.campaignId,
        title: input.title,
        report_type: input.reportType ?? DEFAULT_REPORT_TYPE,
      }
      if (input.artistId) payload.artist = input.artistId
      if (input.trackId) payload.track = input.trackId
      const metadata = buildMetadata(input, input.title)
      if (metadata) payload.metadata = metadata
      const raw = await apiClient.post<RawReport>('/reports/', payload)
      return projectReport(raw)
    }
    case 'media_kit_request': {
      const payload: Record<string, unknown> = {
        campaign: input.campaignId,
        artist: input.artistId,
        title: input.title,
      }
      if (input.trackId) payload.track = input.trackId
      const metadata = buildMetadata(input, input.title)
      if (metadata) payload.metadata = metadata
      const raw = await apiClient.post<RawMediaKit>('/media-kits/', payload)
      return projectMediaKit(raw)
    }
    case 'content_pack': {
      const payload: Record<string, unknown> = {
        campaign: input.campaignId,
        content_pack: input.contentPackId,
      }
      if (input.artistId) payload.artist = input.artistId
      if (input.trackId) payload.track = input.trackId
      const metadata = buildMetadata(input, input.title)
      if (metadata) payload.metadata = metadata
      const raw = await apiClient.post<RawContentPackRequest>(
        '/content-pack-requests/',
        payload,
      )
      return projectContentPackRequest(raw)
    }
  }
}

// ------------------------------ update ------------------------------------

/**
 * Update a (supported, updatable) action. Only reports and media kits expose
 * PATCH; content-pack-requests are immutable (read-only status), so updating
 * one throws rather than silently faking success.
 */
export async function updateCampaignAction(
  input: UpdateCampaignActionInput,
): Promise<CampaignAction> {
  const body: Record<string, unknown> = {}
  if (input.status !== undefined) body.status = input.status
  if (input.metadata !== undefined) body.metadata = input.metadata

  switch (input.type) {
    case 'report_request': {
      const raw = await apiClient.patch<RawReport>(
        `/reports/${input.id}/`,
        body,
      )
      return projectReport(raw)
    }
    case 'media_kit_request': {
      const raw = await apiClient.patch<RawMediaKit>(
        `/media-kits/${input.id}/`,
        body,
      )
      return projectMediaKit(raw)
    }
    case 'content_pack':
      throw new Error(
        'content_pack actions are not updatable: the Backend Core content-pack-request status is read-only.',
      )
  }
}
