import type { CampaignRecommendation } from '@/entities/campaign'
import type {
  CampaignActionPriority,
  RecommendationLike,
  RecommendationRef,
} from '@/entities/campaign-action'
import { deriveRecommendationRef } from '../../entities/campaign-action/recommendation-ref.ts'
import type { Metadata, UUID } from '@/shared/types'

export const DEFAULT_CAMPAIGN_ACTION_PRIORITY: CampaignActionPriority = 'medium'

/** Kept below the backend's 65,536-byte hard limit for encoding headroom. */
export const MAX_RECOMMENDATION_SNAPSHOT_BYTES = 60 * 1024

const MAX_SNAPSHOT_FIELD_BYTES = 12 * 1024
const MAX_NESTING_DEPTH = 6
const MAX_COLLECTION_ITEMS = 50

const SNAPSHOT_FIELDS = [
  'id',
  'title',
  'label',
  'action',
  'type',
  'description',
  'reason',
  'priority',
  'confidence',
] as const

const SENSITIVE_KEYS = new Set([
  'token',
  'access_token',
  'refresh_token',
  'api_key',
  'password',
  'secret',
  'authorization',
  'private_key',
  'client_secret',
  'internal_api_token',
  'x_internal_token',
])

type SafeJsonValue =
  | string
  | number
  | boolean
  | null
  | SafeJsonValue[]
  | { [key: string]: SafeJsonValue }

export interface RecommendationCampaignActionContext {
  recommendationRef: RecommendationRef
  recommendationSnapshot: Metadata
  priority: CampaignActionPriority
}

function normalizedKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).byteLength
}

function truncateUtf8(value: string, maxBytes: number): string {
  if (utf8ByteLength(value) <= maxBytes) return value

  const characters = Array.from(value)
  let low = 0
  let high = characters.length
  while (low < high) {
    const midpoint = Math.ceil((low + high) / 2)
    if (utf8ByteLength(characters.slice(0, midpoint).join('')) <= maxBytes) {
      low = midpoint
    } else {
      high = midpoint - 1
    }
  }
  return characters.slice(0, low).join('')
}

function sanitizeSnapshotValue(
  value: unknown,
  depth: number,
  seen: WeakSet<object>,
): SafeJsonValue | undefined {
  if (value === null) return null
  if (typeof value === 'string') {
    const normalized = value.trim()
    return normalized
      ? truncateUtf8(normalized, MAX_SNAPSHOT_FIELD_BYTES)
      : undefined
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : undefined
  }
  if (typeof value === 'boolean') return value
  if (typeof value !== 'object' || depth >= MAX_NESTING_DEPTH) return undefined
  if (seen.has(value)) return undefined

  seen.add(value)
  try {
    if (Array.isArray(value)) {
      const result: SafeJsonValue[] = []
      for (const item of value) {
        if (result.length >= MAX_COLLECTION_ITEMS) break
        const sanitized = sanitizeSnapshotValue(item, depth + 1, seen)
        if (sanitized !== undefined) result.push(sanitized)
      }
      return result.length > 0 ? result : undefined
    }

    const result: Record<string, SafeJsonValue> = Object.create(null)
    let itemCount = 0
    for (const [key, child] of Object.entries(value)) {
      if (itemCount >= MAX_COLLECTION_ITEMS) break
      if (SENSITIVE_KEYS.has(normalizedKey(key))) continue
      const sanitized = sanitizeSnapshotValue(child, depth + 1, seen)
      if (sanitized === undefined) continue
      result[key] = sanitized
      itemCount += 1
    }
    return Object.keys(result).length > 0 ? result : undefined
  } finally {
    seen.delete(value)
  }
}

function serializedByteLength(value: unknown): number {
  return utf8ByteLength(JSON.stringify(value))
}

function sanitizeAllowlistedField(value: unknown): SafeJsonValue | undefined {
  const sanitized = sanitizeSnapshotValue(value, 0, new WeakSet())
  if (sanitized === undefined || sanitized === null) return undefined
  if (serializedByteLength(sanitized) > MAX_SNAPSHOT_FIELD_BYTES) {
    return undefined
  }
  return sanitized
}

/** Normalize flexible intelligence priorities to the persistent API enum. */
export function normalizeCampaignActionPriority(
  value: unknown,
): CampaignActionPriority {
  if (typeof value === 'number' && Number.isFinite(value)) {
    if (value <= 1) return 'low'
    if (value <= 2) return 'medium'
    if (value <= 3) return 'high'
    return 'urgent'
  }

  if (typeof value !== 'string') return DEFAULT_CAMPAIGN_ACTION_PRIORITY
  const normalized = value.trim().toLowerCase()
  if (!normalized) return DEFAULT_CAMPAIGN_ACTION_PRIORITY
  if (/urgent|critical|immediate|severe/.test(normalized)) return 'urgent'
  if (/\bhigh\b/.test(normalized)) return 'high'
  if (/\blow\b/.test(normalized)) return 'low'
  if (/medium|normal|moderate/.test(normalized)) return 'medium'

  const numeric = Number.parseFloat(normalized.replace(/[^0-9.-]+/g, ''))
  return Number.isFinite(numeric)
    ? normalizeCampaignActionPriority(numeric)
    : DEFAULT_CAMPAIGN_ACTION_PRIORITY
}

/** Build a minimal, recursively sanitized and size-bounded snapshot. */
export function buildRecommendationSnapshot(
  recommendation: CampaignRecommendation | undefined,
): Metadata {
  const source: Record<string, unknown> = recommendation ?? {}
  const snapshot: Metadata = {}

  for (const field of SNAPSHOT_FIELDS) {
    const rawValue =
      field === 'priority'
        ? normalizeCampaignActionPriority(source.priority)
        : source[field]
    const sanitized = sanitizeAllowlistedField(rawValue)
    if (sanitized !== undefined) snapshot[field] = sanitized
  }

  const removableFields = [
    'reason',
    'description',
    'label',
    'action',
    'type',
    'confidence',
  ] as const
  for (const field of removableFields) {
    if (serializedByteLength(snapshot) < MAX_RECOMMENDATION_SNAPSHOT_BYTES) {
      break
    }
    delete snapshot[field]
  }

  if (
    Object.keys(snapshot).length === 0 ||
    serializedByteLength(snapshot) >= MAX_RECOMMENDATION_SNAPSHOT_BYTES
  ) {
    return {
      title: 'Recommendation',
      priority: DEFAULT_CAMPAIGN_ACTION_PRIORITY,
    }
  }

  return snapshot
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function toRecommendationLike(
  recommendation: CampaignRecommendation | undefined,
): RecommendationLike {
  const source: Record<string, unknown> = recommendation ?? {}
  const id = source.id
  return {
    id:
      typeof id === 'string' || typeof id === 'number' ? id : undefined,
    title: asString(source.title),
    label: asString(source.label),
    action: asString(source.action),
    type: asString(source.type),
  }
}

/** Build the correlation fields shared by future CampaignAction create flows. */
export function buildRecommendationCampaignActionContext(
  campaignId: UUID,
  recommendation: CampaignRecommendation | undefined,
  index: number,
): RecommendationCampaignActionContext {
  return {
    recommendationRef: deriveRecommendationRef(
      campaignId,
      toRecommendationLike(recommendation),
      index,
    ),
    recommendationSnapshot: buildRecommendationSnapshot(recommendation),
    priority: normalizeCampaignActionPriority(recommendation?.priority),
  }
}
