/**
 * Domain types for the job envelope exchanged with the Backend Core (Django).
 *
 * These mirror the contracts in the backlog (sections 7, 9, 10). They are kept
 * deliberately decoupled from any Django model — the renderer only understands
 * this envelope and never imports backend models or touches its database.
 */

/** Job types supported by this renderer in the MVP. */
export const SUPPORTED_JOB_TYPES = [
  'content_generation',
  'report_generation',
  'media_kit_generation',
] as const;

export type SupportedJobType = (typeof SUPPORTED_JOB_TYPES)[number];

/** Public alias for the supported job-type union (matches the contract naming). */
export type JobType = SupportedJobType;

export function isSupportedJobType(value: string): value is SupportedJobType {
  return (SUPPORTED_JOB_TYPES as readonly string[]).includes(value);
}

/** The entity in the Backend Core this job is rendering for. */
export interface JobEntity {
  type: string;
  id: string;
}

/** Incoming job envelope (request body from Django). */
export interface JobEnvelope {
  job_id: string;
  workspace_id: string;
  request_id: string;
  job_type: string;
  callback_url: string;
  entity: JobEntity;
  payload_version: string;
  payload: Record<string, unknown>;
}

/** Storage/asset metadata returned to Django so it can create an Asset. */
export interface AssetMetadata {
  storage_provider: 'local';
  bucket: string;
  storage_key: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  checksum: string;
  /** Optional dev-only URL where the file can be fetched (local /files server). */
  public_url?: string;
}

export type OutputStatus = 'completed' | 'failed';

/** A single generated output within a job result. */
export interface RenderOutput {
  output_type: string;
  format: string;
  status: OutputStatus;
  title?: string;
  caption?: string;
  cta?: string;
  required?: boolean;
  /** Template actually used / best compatible value (Django resolves by this). */
  template_key?: string;
  /**
   * Template id echoed from the request (payload `templates[]` or
   * `expected_outputs[]`). Only present when received — never invented, since the
   * renderer's registry has no ids of its own. Django can resolve a Template by
   * this when present (see R-HARD-004).
   */
  template_id?: string;
  asset?: AssetMetadata;
  metadata?: Record<string, unknown>;
}

/**
 * Shape of `result` in the Django callback.
 *
 * Two forms, matching what the Backend Core reads per job type:
 *  - content_generation → `result.outputs[]` (each output may carry an `asset`);
 *  - report_generation / media_kit_generation → a single `result.asset` block
 *    (Django's reports/media-kit handler reads `result.asset`).
 */
export interface JobResult {
  outputs?: RenderOutput[];
  /** Single-asset result for report/media-kit (Django reads `result.asset`). */
  asset?: AssetMetadata & { format?: string; title?: string | null };
  metadata?: Record<string, unknown>;
}

export type JobStatus = 'completed' | 'partially_completed' | 'failed';

/**
 * Normalised error shape reported to Django (callback `error`) and reused by the
 * renderer error model. Never carries secrets in `details`.
 */
export interface RenderError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

/**
 * Internal outcome returned by a renderer/dispatcher: the overall job status
 * plus the produced outputs. The controller maps this onto the HTTP response
 * and (in a later pipeline) onto the Django callback.
 */
export interface RenderResult {
  status: JobStatus;
  outputs: RenderOutput[];
}

/** Callback payload sent to Django after a job is rendered. */
export interface CallbackPayload {
  job_id: string;
  workspace_id: string;
  status: JobStatus;
  entity: JobEntity;
  result: JobResult | null;
  error: RenderError | null;
  metadata: {
    renderer: string;
    renderer_version: string;
    [key: string]: unknown;
  };
}
