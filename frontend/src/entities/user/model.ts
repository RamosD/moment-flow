import type { ISODateTimeString, UUID } from '@/shared/types'

/** The authenticated user. Mirrors `User` (read-only) in the Backend Core schema. */
export interface User {
  id: UUID
  email: string
  full_name: string
  display_name: string
  avatar_url: string
  preferred_language: string
  timezone: string
  email_verified_at: ISODateTimeString | null
  is_email_verified: boolean
  is_active: boolean
  is_staff: boolean
  date_joined: ISODateTimeString
  last_login: ISODateTimeString | null
}
