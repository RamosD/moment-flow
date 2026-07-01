/**
 * Build a normalised {@link RenderError} for the Django `failed` callback.
 *
 * Shared by the dispatcher across all job types. Two sources:
 *   - {@link aggregateRenderError}: from a renderer-returned `failed` result
 *     (top-level `code` is the stable `render_failed`; the first failed output's
 *     safe error is surfaced under `details.first_error`);
 *   - {@link renderErrorFromException}: from a thrown {@link AppError} during
 *     dispatch (timeout / unexpected), preserving the precise error `code`.
 *
 * The error `details` are kept small and secret-free; {@link buildFailedPayload}
 * additionally redacts them as defence-in-depth.
 */
import type { AppError } from '../errors/errors';
import type { JobEnvelope, RenderError, RenderResult } from '../jobs/job.types';

const FAILURE_MESSAGES: Record<string, string> = {
  content_generation: 'Falha ao gerar o conteúdo.',
  report_generation: 'Falha ao gerar o relatório.',
  media_kit_generation: 'Falha ao gerar o media kit.',
};

/** Human-friendly failure message for a job type. */
export function failureMessage(jobType: string): string {
  return FAILURE_MESSAGES[jobType] ?? 'Falha ao gerar o output do job.';
}

export function aggregateRenderError(envelope: JobEnvelope, result: RenderResult): RenderError {
  const failedOutputs = result.outputs.filter((o) => o.status === 'failed');
  const firstError = failedOutputs[0]?.metadata?.error;
  return {
    code: 'render_failed',
    message: failureMessage(envelope.job_type),
    details: {
      outputs_total: result.outputs.length,
      outputs_failed: failedOutputs.length,
      ...(firstError ? { first_error: firstError } : {}),
    },
  };
}

/** Normalised error from a thrown {@link AppError} during render dispatch. */
export function renderErrorFromException(envelope: JobEnvelope, error: AppError): RenderError {
  return {
    code: error.code,
    message: failureMessage(envelope.job_type),
    details: {
      operation: 'render',
      reason: error.code,
    },
  };
}
