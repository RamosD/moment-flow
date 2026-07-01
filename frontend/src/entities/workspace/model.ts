import type { ISODateTimeString, Metadata, UUID } from '@/shared/types'

export type WorkspaceType =
  | 'artist'
  | 'manager'
  | 'label'
  | 'distributor'
  | 'agency'
  | 'media'
  | 'white_label'
  | 'internal'

export type WorkspaceStatus =
  | 'active'
  | 'trial'
  | 'suspended'
  | 'cancelled'
  | 'archived'

/** A workspace (tenant). Mirrors `Workspace` in the Backend Core schema. */
export interface Workspace {
  id: UUID
  name: string
  slug: string
  status: WorkspaceStatus
  created_by: UUID | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  workspace_type?: WorkspaceType
  country?: string
  market?: string
  default_language?: string
  timezone?: string
  metadata?: Metadata
}
