/**
 * Callback client (CR-503 / R-HARD-006).
 *
 * POSTs the render result back to the Backend Core (Django) `callback_url` with
 * the internal token header and a per-attempt timeout
 * (`CALLBACK_TIMEOUT_SECONDS`), retrying transient failures with a simple
 * exponential backoff (`CALLBACK_MAX_ATTEMPTS`, `CALLBACK_RETRY_BASE_DELAY_MS`,
 * `CALLBACK_RETRY_MAX_DELAY_MS`).
 *
 * Retry policy:
 *   - RETRY on network error, timeout and HTTP 500/502/503/504;
 *   - DO NOT retry on 4xx (400/401/403/404/409/422, …) — a 4xx is reported as a
 *     non-delivery, never masked as success;
 *   - 2xx → delivered.
 * Total time is bounded by `attempts × (timeout + backoff)` — never an infinite
 * loop, and `send` never blocks indefinitely.
 *
 * Non-fatal: `send` NEVER throws. It always resolves with a {@link CallbackResult}
 * (`ok`, last `statusCode`, `attempts`) so the JobService can log the outcome and
 * keep the rendered files regardless of delivery success.
 *
 * Security: the internal token travels in the `X-Internal-Token` header and is
 * NEVER logged. Logs carry only the callback URL, job correlation ids
 * (job_id/workspace_id from the payload), attempt counters and the HTTP status.
 */
import type { AppConfig } from '../config/env';
import type { CallbackPayload } from '../jobs/job.types';
import type { Logger } from '../logging/logger';

export interface CallbackResult {
  /** Whether the callback was ultimately delivered with a 2xx response. */
  ok: boolean;
  /** HTTP status of the last attempt; 0 when there was no HTTP response. */
  statusCode: number;
  /**
   * Number of attempts performed (1..CALLBACK_MAX_ATTEMPTS). Always set by the
   * real client; optional so lightweight test doubles may omit it.
   */
  attempts?: number;
}

export interface CallbackClient {
  send(callbackUrl: string, payload: CallbackPayload): Promise<CallbackResult>;
}

export interface CallbackClientDeps {
  config: AppConfig;
  logger: Logger;
}

/** HTTP statuses worth retrying (transient server-side / gateway failures). */
const RETRYABLE_STATUS = new Set([500, 502, 503, 504]);

function isTimeout(err: unknown): boolean {
  return err instanceof Error && (err.name === 'TimeoutError' || err.name === 'AbortError');
}

function sleep(ms: number): Promise<void> {
  if (ms <= 0) {
    return Promise.resolve();
  }
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function createCallbackClient(deps: CallbackClientDeps): CallbackClient {
  const { config, logger } = deps;
  const timeoutMs = Math.max(1, Math.round(config.callbackTimeoutSeconds * 1000));
  const maxAttempts = Math.max(1, config.callbackMaxAttempts);
  const baseDelayMs = Math.max(0, config.callbackRetryBaseDelayMs);
  const maxDelayMs = Math.max(baseDelayMs, config.callbackRetryMaxDelayMs);

  /** Exponential backoff for the delay AFTER the given (1-based) failed attempt. */
  function backoffDelay(attempt: number): number {
    const exp = baseDelayMs * 2 ** (attempt - 1);
    return Math.min(maxDelayMs, exp);
  }

  async function send(callbackUrl: string, payload: CallbackPayload): Promise<CallbackResult> {
    const baseLog = {
      callback_url: callbackUrl,
      job_id: payload.job_id,
      workspace_id: payload.workspace_id,
      status: payload.status,
    };

    let lastStatus = 0;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const attemptLog = { ...baseLog, attempt, max_attempts: maxAttempts };
      logger.info('callback.attempt_started', attemptLog);

      try {
        const response = await fetch(callbackUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Internal-Token': config.internalApiToken,
          },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(timeoutMs),
        });
        lastStatus = response.status;

        if (response.ok) {
          logger.info('callback.completed', { ...attemptLog, http_status: response.status });
          return { ok: true, statusCode: response.status, attempts: attempt };
        }

        // Non-2xx response.
        const retryable = RETRYABLE_STATUS.has(response.status);
        logger.warn('callback.attempt_failed', {
          ...attemptLog,
          http_status: response.status,
          retryable,
        });

        if (retryable && attempt < maxAttempts) {
          const delayMs = backoffDelay(attempt);
          logger.info('callback.retry_scheduled', {
            ...attemptLog,
            next_attempt: attempt + 1,
            delay_ms: delayMs,
          });
          await sleep(delayMs);
          continue;
        }

        // Non-retryable (4xx) or attempts exhausted: a real delivery failure.
        logger.error('callback.delivery_failed', {
          ...attemptLog,
          http_status: response.status,
          reason: retryable ? 'max_attempts_exhausted' : 'non_retryable_status',
        });
        return { ok: false, statusCode: response.status, attempts: attempt };
      } catch (err) {
        // Network error or per-attempt timeout — always retryable.
        const reason = isTimeout(err) ? 'timeout' : 'network_error';
        logger.warn('callback.attempt_failed', {
          ...attemptLog,
          error: reason,
          ...(reason === 'timeout' ? { timeout_ms: timeoutMs } : {}),
        });

        if (attempt < maxAttempts) {
          const delayMs = backoffDelay(attempt);
          logger.info('callback.retry_scheduled', {
            ...attemptLog,
            next_attempt: attempt + 1,
            delay_ms: delayMs,
          });
          await sleep(delayMs);
          continue;
        }

        logger.error('callback.delivery_failed', { ...attemptLog, reason });
        return { ok: false, statusCode: 0, attempts: attempt };
      }
    }

    // Defensive fallback (unreachable: the loop always returns when maxAttempts >= 1).
    logger.error('callback.delivery_failed', {
      ...baseLog,
      attempt: maxAttempts,
      max_attempts: maxAttempts,
      reason: 'exhausted',
    });
    return { ok: false, statusCode: lastStatus, attempts: maxAttempts };
  }

  return { send };
}
