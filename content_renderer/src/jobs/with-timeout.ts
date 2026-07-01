/**
 * Bound an async operation by a timeout (CR-203 / hardening).
 *
 * Races `promise` against a timer; if the timer wins, rejects with a normalised
 * {@link TimeoutError}. Note: this bounds how long the caller WAITS — it does not
 * cancel the underlying work (the renderers have no cancellation token in the
 * MVP). It is a safety net so a runaway render still yields a `timeout` callback
 * instead of hanging the request.
 */
import { TimeoutError } from '../errors/errors';

export function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  details: Record<string, unknown> = {},
): Promise<T> {
  const ms = Math.max(1, Math.round(timeoutMs));
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new TimeoutError('Operation timed out.', { timeout_ms: ms, ...details }));
    }, ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}
