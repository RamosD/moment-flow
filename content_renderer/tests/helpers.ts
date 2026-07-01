/**
 * Shared test helpers for the background-execution flow (R-HARD-001).
 *
 * Since `POST /jobs` now returns `202` and runs render → storage → callback on a
 * later tick (`setImmediate`), tests must wait for that background work to land
 * before asserting on the recorded callback / logs. These helpers keep that
 * waiting deterministic without arbitrary fixed sleeps.
 */

/** A promise plus its externally callable resolver — a classic deferred. */
export interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
}

export function createDeferred<T = void>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

/**
 * Poll `condition` until it returns true or the timeout elapses. Used to wait
 * for a background callback/log to be produced after a 202 response.
 */
export async function waitUntil(
  condition: () => boolean,
  { timeoutMs = 10_000, intervalMs = 5 }: { timeoutMs?: number; intervalMs?: number } = {},
): Promise<void> {
  const start = Date.now();
  while (!condition()) {
    if (Date.now() - start > timeoutMs) {
      throw new Error('waitUntil: condition not met within timeout');
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
