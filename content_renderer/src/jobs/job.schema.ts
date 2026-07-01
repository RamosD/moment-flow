/**
 * Zod schema for the job envelope (backlog CR-103).
 *
 * This schema is the single source of truth for envelope validation and is
 * intentionally reusable from tests. The actual wiring into `POST /jobs` is
 * delivered by a later pipeline; this file only defines and exposes the schema
 * and a convenience parser.
 */
import { z } from 'zod';

export const jobEntitySchema = z
  .object({
    type: z.string().min(1, 'entity.type is required'),
    id: z.string().min(1, 'entity.id is required'),
  })
  .strict();

export const jobEnvelopeSchema = z
  .object({
    job_id: z.string().min(1, 'job_id is required'),
    workspace_id: z.string().min(1, 'workspace_id is required'),
    request_id: z.string().min(1, 'request_id is required'),
    job_type: z.string().min(1, 'job_type is required'),
    callback_url: z.string().url('callback_url must be a valid URL'),
    entity: jobEntitySchema,
    payload_version: z.string().min(1, 'payload_version is required'),
    payload: z.record(z.string(), z.unknown()),
  })
  .strict();

export type JobEnvelopeInput = z.infer<typeof jobEnvelopeSchema>;

export type ParseResult<T> =
  | { success: true; data: T }
  | { success: false; error: z.ZodError };

/** Safe-parse helper returning a discriminated result instead of throwing. */
export function parseJobEnvelope(input: unknown): ParseResult<JobEnvelopeInput> {
  const result = jobEnvelopeSchema.safeParse(input);
  if (result.success) {
    return { success: true, data: result.data };
  }
  return { success: false, error: result.error };
}
