import type {
  ISODateString,
  ISODateTimeString,
  Metadata,
  UUID,
} from '@/shared/types'

export type TrackType =
  | 'single'
  | 'music_video'
  | 'album_track'
  | 'remix'
  | 'live'
  | 'freestyle'
  | 'other'

export type TrackStatus =
  | 'draft'
  | 'scheduled'
  | 'released'
  | 'monitoring'
  | 'paused'
  | 'archived'

/** A track. Mirrors `Track` in the Backend Core schema. */
export interface Track {
  id: UUID
  workspace: UUID
  artist: UUID
  title: string
  slug: string
  created_by: UUID | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  release_date?: ISODateString | null
  track_type?: TrackType
  primary_genre?: string
  language?: string
  market?: string
  cover_asset?: UUID | null
  status?: TrackStatus
  metadata?: Metadata
}
