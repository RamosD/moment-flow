/**
 * Builders for the Django callback payloads (backlog section 9).
 *
 * Centralising construction keeps the success/failure contract in one tested
 * place. The renderer name/version are stamped into `metadata`.
 */
import { RENDERER_NAME, RENDERER_VERSION } from '../constants';
import { redact } from '../logging/logger';
import type {
  CallbackPayload,
  JobEnvelope,
  JobResult,
  RenderError,
  RenderResult,
} from '../jobs/job.types';

/** Job types whose Django handler reads a single `result.asset` (not `outputs`). */
const SINGLE_ASSET_JOB_TYPES = new Set(['report_generation', 'media_kit_generation']);

/**
 * Shape the `result` field per the Backend Core contract:
 *  - report/media-kit → `{ asset, metadata }` (Django reads `result.asset`);
 *  - content (and anything else) → `{ outputs }`.
 */
function buildResultField(envelope: JobEnvelope, result: RenderResult): JobResult {
  if (SINGLE_ASSET_JOB_TYPES.has(envelope.job_type)) {
    const doc = result.outputs.find((o) => o.status === 'completed' && o.asset);
    if (doc?.asset) {
      return {
        asset: { ...doc.asset, format: doc.format, title: doc.title ?? null },
        metadata: doc.metadata ?? {},
      };
    }
  }
  return { outputs: result.outputs };
}

/** Build a `completed` / `partially_completed` callback from a render result. */
export function buildCompletedPayload(
  envelope: JobEnvelope,
  result: RenderResult,
): CallbackPayload {
  return {
    job_id: envelope.job_id,
    workspace_id: envelope.workspace_id,
    status: result.status,
    entity: envelope.entity,
    result: buildResultField(envelope, result),
    error: null,
    metadata: {
      renderer: RENDERER_NAME,
      renderer_version: RENDERER_VERSION,
    },
  };
}

/**
 * Build a `failed` callback from a normalised render error. The error `details`
 * are passed through {@link redact} as a defence-in-depth safeguard so no
 * secret-shaped value (token, password, api key, …) can ever reach Django.
 */
export function buildFailedPayload(envelope: JobEnvelope, error: RenderError): CallbackPayload {
  const safeError: RenderError = {
    code: error.code,
    message: error.message,
    details: (redact(error.details) as Record<string, unknown>) ?? {},
  };
  return {
    job_id: envelope.job_id,
    workspace_id: envelope.workspace_id,
    status: 'failed',
    entity: envelope.entity,
    result: null,
    error: safeError,
    metadata: {
      renderer: RENDERER_NAME,
      renderer_version: RENDERER_VERSION,
    },
  };
}
