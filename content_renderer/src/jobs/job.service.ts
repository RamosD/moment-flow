/**
 * Job service / dispatcher (CR-202 / CR-203 / CR-503 / R-HARD-001).
 *
 * Separates the three responsibilities of a job's lifecycle so the HTTP layer
 * can respond `202 Accepted` quickly and never races the Django callback:
 *
 *   1. {@link JobService.acceptJob}          — reception gate (synchronous):
 *      validates the job can be accepted (unknown `job_type` is declined 400 with
 *      NO callback), logs `job.accepted` and returns the job-scoped context.
 *   2. {@link JobService.scheduleJobExecution} — scheduling (non-blocking):
 *      logs `job.scheduled` and detaches the render/callback onto a light-weight
 *      background tick (`setImmediate`). Returns immediately.
 *   3. {@link JobService.executeJob}          — execution (background):
 *      render → storage → callback. Bounds the render by `RENDER_TIMEOUT_SECONDS`
 *      and delivers the result to the Backend Core (Django) via the callback
 *      client:
 *        - `completed` / `partially_completed` → success callback with `result.outputs`;
 *        - `failed`                            → failure callback with a normalised error.
 *
 * Robustness:
 *   - A render that throws or times out is caught, normalised (preserving the
 *     `timeout` / error code) and reported as a `failed` callback.
 *   - Callback delivery is best-effort and NON-FATAL: a callback failure is
 *     logged but never discards the rendered files (risk 14.5).
 *   - The background tick has a global safety net ({@link JobService} internal
 *     `runInBackground`): any unexpected throw is caught, logged as
 *     `job.execution_failed`, triggers a best-effort `failed` callback and NEVER
 *     crashes the process (RSK-HARD-001).
 *
 * Lifecycle logs (job.accepted, job.scheduled, render.started/completed/failed,
 * callback.started/completed/failed, job.execution_failed) all carry job_id,
 * workspace_id, request_id and job_type via the child logger, and never the
 * internal token (the logger also redacts secret-shaped keys defensively).
 */
import { buildCompletedPayload, buildFailedPayload } from '../callbacks/callback.payload';
import type { CallbackClient } from '../callbacks/callback.client';
import {
  aggregateRenderError,
  renderErrorFromException,
} from '../callbacks/render-error';
import type { AppConfig } from '../config/env';
import {
  AppError,
  UnsupportedJobTypeError,
  toAppError,
} from '../errors/errors';
import type { Logger } from '../logging/logger';
import { renderContentGeneration } from '../renderers/content';
import { renderMediaKitGeneration } from '../renderers/media-kits';
import { renderReportGeneration } from '../renderers/reports';
import type { Renderer, RenderContext } from '../renderers/renderer.types';
import type { StorageProvider } from '../storage/storage.types';
import {
  isSupportedJobType,
  type JobEnvelope,
  type RenderError,
  type RenderResult,
  type SupportedJobType,
} from './job.types';
import { withTimeout } from './with-timeout';

export interface JobServiceDeps {
  config: AppConfig;
  logger: Logger;
  storage: StorageProvider;
  callbackClient: CallbackClient;
  /** Override renderers (tests). Defaults to the real renderers. */
  renderers?: Partial<Record<SupportedJobType, Renderer>>;
}

/**
 * Job-scoped execution context handed from acceptance through to background
 * execution. Carries the child logger bound to the job correlation ids so every
 * lifecycle log line is traceable.
 */
export interface JobExecutionContext {
  logger: Logger;
}

export interface JobService {
  /**
   * Reception gate (synchronous). Validates that the job can be accepted, logs
   * `job.accepted` and returns the job-scoped {@link JobExecutionContext}.
   * Throws {@link UnsupportedJobTypeError} for unknown job types so the
   * controller returns a controlled 400 and NO callback is ever sent (the job
   * was declined, not accepted).
   */
  acceptJob(envelope: JobEnvelope): JobExecutionContext;

  /**
   * Schedule the render → storage → callback pipeline to run in a light-weight
   * background tick (`setImmediate`). Non-blocking: returns immediately so the
   * HTTP layer can answer `202` without waiting for the callback. Any unexpected
   * error in the background is caught and never crashes the process.
   */
  scheduleJobExecution(envelope: JobEnvelope, context?: JobExecutionContext): void;

  /**
   * Execute the full render → storage → callback pipeline for an accepted job.
   * Resolves with the {@link RenderResult}. Render failures are reported as
   * `failed` callbacks (not thrown). Exposed for direct use in tests and
   * synchronous flows; the HTTP path always goes through
   * {@link JobService.scheduleJobExecution}.
   */
  executeJob(envelope: JobEnvelope, context?: JobExecutionContext): Promise<RenderResult>;
}

/** Output type echoed for a fully-failed (thrown) render, per job type. */
const FAILED_OUTPUT_TYPE: Record<SupportedJobType, string> = {
  content_generation: 'post',
  report_generation: 'report',
  media_kit_generation: 'media_kit',
};

export function createJobService(deps: JobServiceDeps): JobService {
  const { config, logger, storage, callbackClient } = deps;

  const renderers: Record<SupportedJobType, Renderer> = {
    content_generation: renderContentGeneration,
    report_generation: renderReportGeneration,
    media_kit_generation: renderMediaKitGeneration,
    ...deps.renderers,
  };

  const renderTimeoutMs = Math.max(1, Math.round(config.renderTimeoutSeconds * 1000));

  /** Build the job-scoped child logger / context from an envelope. */
  function buildContext(envelope: JobEnvelope): JobExecutionContext {
    return {
      logger: logger.child({
        job_id: envelope.job_id,
        workspace_id: envelope.workspace_id,
        request_id: envelope.request_id,
        job_type: envelope.job_type,
      }),
    };
  }

  /** Build the failed result echoed when a render throws / times out. */
  function buildFailedResult(jobType: SupportedJobType, appError: AppError): RenderResult {
    return {
      status: 'failed',
      outputs: [
        {
          output_type: FAILED_OUTPUT_TYPE[jobType],
          format: '',
          status: 'failed',
          required: true,
          metadata: { error: { code: appError.code, message: appError.message } },
        },
      ],
    };
  }

  function acceptJob(envelope: JobEnvelope): JobExecutionContext {
    if (!isSupportedJobType(envelope.job_type)) {
      // Declined up-front: no callback is sent for a job we never accepted.
      throw new UnsupportedJobTypeError(envelope.job_type);
    }
    const context = buildContext(envelope);
    context.logger.info('job.accepted', {});
    return context;
  }

  function scheduleJobExecution(envelope: JobEnvelope, context?: JobExecutionContext): void {
    const ctx = context ?? buildContext(envelope);
    ctx.logger.info('job.scheduled', {});
    // Light-weight background execution: detach from the HTTP request lifecycle
    // (no external queue — backlog forbids BullMQ/Redis/RabbitMQ/Kafka). The
    // 202 is already (about to be) returned; render + callback run on the next
    // tick. The error handler below is the global safety net (RSK-HARD-001).
    setImmediate(() => {
      void runInBackground(envelope, ctx);
    });
  }

  /**
   * Background runner: invokes {@link executeJob} and guarantees the process is
   * never brought down by an unexpected throw. `executeJob` is designed never to
   * reject, so reaching the catch means a genuinely unexpected failure (e.g. a
   * logging sink blowing up) — it is logged and a best-effort `failed` callback
   * is attempted so Django is not left waiting.
   */
  async function runInBackground(envelope: JobEnvelope, context: JobExecutionContext): Promise<void> {
    try {
      await executeJob(envelope, context);
    } catch (err) {
      const appError = toAppError(err);
      context.logger.error('job.execution_failed', { code: appError.code });
      if (isSupportedJobType(envelope.job_type)) {
        try {
          await deliverCallback(
            envelope,
            buildFailedResult(envelope.job_type, appError),
            context.logger,
            renderErrorFromException(envelope, appError),
          );
        } catch {
          // deliverCallback already logs delivery failures; never rethrow from
          // the safety net.
        }
      }
    }
  }

  async function executeJob(
    envelope: JobEnvelope,
    context: JobExecutionContext = buildContext(envelope),
  ): Promise<RenderResult> {
    const jobType = envelope.job_type as SupportedJobType;
    const jobLogger = context.logger;
    const renderContext: RenderContext = { config, logger: jobLogger, storage };
    const renderer = renderers[jobType];

    let result: RenderResult;
    try {
      jobLogger.info('render.started', {});
      result = await withTimeout(renderer(envelope, renderContext), renderTimeoutMs, {
        operation: 'render',
        job_type: jobType,
      });
      jobLogger.info('render.completed', {
        status: result.status,
        outputs: result.outputs.length,
      });
    } catch (err) {
      // Timeout or unexpected throw → normalised failed callback (never crash).
      const appError: AppError = toAppError(err);
      jobLogger.error('render.failed', { code: appError.code });
      result = buildFailedResult(jobType, appError);
      await deliverCallback(envelope, result, jobLogger, renderErrorFromException(envelope, appError));
      return result;
    }

    await deliverCallback(envelope, result, jobLogger);
    return result;
  }

  /**
   * Build and send the appropriate callback. `explicitError` overrides the
   * aggregated error (used for thrown/timeout failures so the precise code is
   * preserved). Delivery failures are logged, not thrown.
   */
  async function deliverCallback(
    envelope: JobEnvelope,
    result: RenderResult,
    jobLogger: Logger,
    explicitError?: RenderError,
  ): Promise<void> {
    const payload =
      result.status === 'failed'
        ? buildFailedPayload(envelope, explicitError ?? aggregateRenderError(envelope, result))
        : buildCompletedPayload(envelope, result);

    jobLogger.info('callback.started', { status: payload.status });
    try {
      const result = await callbackClient.send(envelope.callback_url, payload);
      if (result.ok) {
        jobLogger.info('callback.completed', {
          status: payload.status,
          http_status: result.statusCode,
          attempts: result.attempts,
        });
      } else {
        // Delivery exhausted retries / hit a non-retryable status. Non-fatal:
        // the rendered files remain in storage; do not fail the job.
        jobLogger.error('callback.failed', {
          status: payload.status,
          http_status: result.statusCode,
          attempts: result.attempts,
        });
      }
    } catch (err) {
      // Defensive: the real client never throws (it returns ok:false), but a
      // faulty injected client might. Still non-fatal.
      jobLogger.error('callback.failed', {
        status: payload.status,
        error_code: err instanceof AppError ? err.code : 'callback_failed',
      });
    }
  }

  return { acceptJob, scheduleJobExecution, executeJob };
}
