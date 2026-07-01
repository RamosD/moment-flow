import type { ISODateTimeString, Metadata, UUID } from '@/shared/types'

/**
 * A catalogue content pack. Mirrors `ContentPack` in the Backend Core schema
 * (`GET /content-packs/`). Read-only reference data — global or workspace-owned
 * rows the user can request a generation from. Only the fields the UI renders
 * are typed; the rest of the schema is intentionally omitted.
 */
export interface ContentPack {
  id: UUID
  name: string
  pack_key: string
  // Optional in practice for our use — render defensively.
  description?: string
  pack_type?: string
  status?: string
  is_premium?: boolean
  metadata?: Metadata
  created_at?: ISODateTimeString
  updated_at?: ISODateTimeString
}
