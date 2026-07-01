import type { ISODateTimeString, Metadata, UUID } from '@/shared/types'

export type ArtistStatus = 'active' | 'inactive' | 'archived'

/** An artist. Mirrors `Artist` in the Backend Core schema. */
export interface Artist {
  id: UUID
  workspace: UUID
  name: string
  slug: string
  created_by: UUID | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  country?: string
  market?: string
  primary_genre?: string
  language?: string
  bio_short?: string
  bio_long?: string
  image_asset?: UUID | null
  status?: ArtistStatus
  metadata?: Metadata
}
