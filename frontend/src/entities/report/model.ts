import type {
  ISODateString,
  ISODateTimeString,
  Metadata,
  UUID,
} from '@/shared/types'

export type ReportType =
  | 'weekly_report'
  | 'monthly_report'
  | 'campaign_report'
  | 'artist_report'
  | 'track_report'
  | 'label_report'
  | 'catalogue_report'

export type ReportStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'archived'

/** A generated report. Mirrors `Report` in the Backend Core schema. */
export interface Report {
  id: UUID
  workspace: UUID
  report_type: ReportType
  title: string
  requested_by: UUID | null
  created_at: ISODateTimeString
  updated_at: ISODateTimeString
  // Optional in the contract:
  campaign?: UUID | null
  artist?: UUID | null
  track?: UUID | null
  period_start?: ISODateString | null
  period_end?: ISODateString | null
  status?: ReportStatus
  storage_asset?: UUID | null
  metadata?: Metadata
}
