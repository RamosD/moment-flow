import type {
  ISODateTimeString,
  Metadata,
  UUID,
} from '@/shared/types'

export type MediaKitStatus = 'draft' | 'generated' | 'published' | 'archived'

export type MediaKitItemType =
  | 'bio'
  | 'stats'
  | 'image'
  | 'track'
  | 'link'
  | 'press_quote'
  | 'contact'
  | 'achievement'
  | 'other'

/**
 * Visibility scope (also used by content outputs). Duplicated here rather than
 * imported cross-entity, to respect the layer rule (entities → shared only).
 */
export type PublicVisibility = 'private' | 'workspace' | 'public' | 'unlisted'

/** An item within a media kit. Mirrors `MediaKitItem`. */
export interface MediaKitItem {
  id: UUID
  workspace: UUID
  media_kit: UUID
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  item_type?: MediaKitItemType
  title?: string
  content?: string
  asset?: UUID | null
  sort_order?: number
  metadata?: Metadata
}

/** A media kit. Mirrors `MediaKit` in the Backend Core schema. */
export interface MediaKit {
  id: UUID
  workspace: UUID
  artist: UUID
  title: string
  created_by: UUID | null
  /** Read-only nested items (always present in responses). */
  items: MediaKitItem[]
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  campaign?: UUID | null
  track?: UUID | null
  status?: MediaKitStatus
  public_visibility?: PublicVisibility
  storage_asset?: UUID | null
  metadata?: Metadata
}

export interface CreateMediaKitPayload {
  campaign: UUID
  artist: UUID
  title: string
  track?: UUID | null
}
