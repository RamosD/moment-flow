import type {
  ISODateString,
  ISODateTimeString,
  Metadata,
  UUID,
} from '@/shared/types'

export type CampaignType =
  | 'single_release'
  | 'music_video_release'
  | 'album_release'
  | 'milestone_campaign'
  | 'comeback_campaign'
  | 'weekly_growth_campaign'
  | 'catalogue_push'
  | 'media_campaign'
  | 'custom'

export type CampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'active'
  | 'paused'
  | 'completed'
  | 'archived'

/** A campaign. Mirrors `Campaign` in the Backend Core schema. */
export interface Campaign {
  id: UUID
  workspace: UUID
  artist: UUID
  name: string
  slug: string
  created_by: UUID | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  track?: UUID | null
  campaign_type?: CampaignType
  status?: CampaignStatus
  start_date?: ISODateString | null
  end_date?: ISODateString | null
  primary_goal?: string
  description?: string
  metadata?: Metadata
}
