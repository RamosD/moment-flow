import type { ISODateTimeString, Metadata, UUID } from '@/shared/types'

export interface ContentPackRequest {
  id: UUID
  workspace: UUID
  campaign: UUID
  content_pack: UUID
  requested_by: UUID | null
  status: string
  requested_at: ISODateTimeString
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  track?: UUID | null
  artist?: UUID | null
  completed_at?: ISODateTimeString | null
  failed_at?: ISODateTimeString | null
  error_message?: string
  metadata?: Metadata
}

export interface CreateContentPackRequestPayload {
  campaign: UUID
  content_pack: UUID
  track?: UUID | null
  artist?: UUID | null
}
