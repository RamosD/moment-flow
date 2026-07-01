import type {
  ISODateTimeString,
  Metadata,
  UUID,
} from '@/shared/types'

export type ContentOutputStatus =
  | 'queued'
  | 'validating'
  | 'processing'
  | 'rendering'
  | 'uploading'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'expired'
  | 'archived'

/**
 * Visibility scope shared by content outputs and media kits.
 * (Duplicated per entity to keep entities decoupled — see media-kit.)
 */
export type PublicVisibility = 'private' | 'workspace' | 'public' | 'unlisted'

/** A generated content asset for a campaign. Mirrors `ContentOutput`. */
export interface ContentOutput {
  id: UUID
  workspace: UUID
  campaign: UUID
  template: UUID
  output_type: string
  usage_event_id: UUID | null
  created_by: UUID | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  track?: UUID | null
  artist?: UUID | null
  content_pack_request?: UUID | null
  template_version?: UUID | null
  format?: string
  status?: ContentOutputStatus
  title?: string
  caption?: string
  cta?: string
  storage_asset?: UUID | null
  public_visibility?: PublicVisibility
  expires_at?: ISODateTimeString | null
  metadata?: Metadata
}
