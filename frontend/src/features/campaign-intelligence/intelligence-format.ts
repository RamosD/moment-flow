import type {
  CampaignMoment,
  CampaignRecommendation,
  IntelligenceNote,
} from '@/entities/campaign'
import type { BadgeVariant } from '@/shared/ui'

/** "engagement_rate" → "Engagement Rate". */
export function humanizeKey(key: string): string {
  return key
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim()
}

/** True for values we render directly in the score grid (skip nested data). */
export function isPrimitive(value: unknown): value is string | number | boolean {
  return (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  )
}

/** Display a primitive score value; the frontend never computes scores. */
export function formatScoreValue(value: string | number | boolean): string {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(2)
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return value
}

/** Map a grade letter to a badge color. Defensive — unknown grades stay neutral. */
export function gradeVariant(grade?: string | null): BadgeVariant {
  if (!grade) return 'neutral'
  const letter = grade.trim().charAt(0).toUpperCase()
  if (letter === 'A') return 'success'
  if (letter === 'B') return 'info'
  if (letter === 'C') return 'warning'
  if (letter === 'D' || letter === 'E' || letter === 'F') return 'danger'
  return 'primary'
}

function firstString(
  obj: Record<string, unknown>,
  keys: string[],
): string | undefined {
  for (const key of keys) {
    const value = obj[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return undefined
}

/** Best-effort message for a warning/explanation note (free-form in contract). */
export function noteToMessage(note: IntelligenceNote): string {
  return (
    firstString(note, ['message', 'detail', 'text', 'title', 'description', 'code']) ??
    'See details'
  )
}

export function momentTitle(moment: CampaignMoment): string {
  return firstString(moment, ['title', 'label', 'name', 'type']) ?? 'Moment'
}

export function recommendationTitle(rec: CampaignRecommendation): string {
  return firstString(rec, ['title', 'label', 'name', 'type']) ?? 'Recommendation'
}

/** Human label for a priority that may be a number or a string. */
export function formatPriority(priority: unknown): string | null {
  if (typeof priority === 'number') return `Priority ${priority}`
  if (typeof priority === 'string' && priority.trim()) return priority
  return null
}

/** Read a string field defensively (fields are not guaranteed by the contract). */
export function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}
