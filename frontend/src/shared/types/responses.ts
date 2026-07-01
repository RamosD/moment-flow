import type { Paginated } from '@/shared/api'

/**
 * DRF list envelope: `{ count, next, previous, results }`. Re-exported from the
 * transport layer so domain code has a single import surface for responses.
 */
export type PaginatedResponse<T> = Paginated<T>

/** DRF detail endpoints return the entity directly. Alias for readability. */
export type DetailResponse<T> = T

/**
 * Shape of a DRF error body. `detail`/`code` are common; validation errors add
 * arbitrary `{ field: string[] }` entries (captured by the index signature).
 */
export interface ApiErrorResponse {
  detail?: string
  code?: string
  [field: string]: unknown
}
