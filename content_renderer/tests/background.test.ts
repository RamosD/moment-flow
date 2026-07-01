/**
 * Background execution tests (R-HARD-001).
 *
 * Verifies the reception/scheduling/execution split:
 *   - POST /jobs returns 202 BEFORE the callback is delivered;
 *   - the `completed` callback is delivered in the background;
 *   - a render failure delivers a `failed` callback in the background;
 *   - a callback delivery error is non-fatal (the process keeps serving);
 *   - an unexpected background error is caught, logged and never crashes;
 *   - background logs never expose the internal token.
 */
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';

import { createApp } from '../src/app';
import type { CallbackClient } from '../src/callbacks/callback.client';
import { loadConfig, type AppConfig } from '../src/config/env';
import { CallbackFailedError, RenderFailedError, StorageFailedError } from '../src/errors/errors';
import { createJobService } from '../src/jobs/job.service';
import type { CallbackPayload, JobEnvelope } from '../src/jobs/job.types';
import { createLogger } from '../src/logging/logger';
import type { Renderer } from '../src/renderers/renderer.types';
import {
  createLocalStorage,
  type LocalStorage,
  type SaveBufferInput,
} from '../src/storage/local-storage';
import { createDeferred, waitUntil } from './helpers';

const TOKEN = 'test-internal-token';
const silentLogger = createLogger({ write: () => {} });

function configFor(root: string): AppConfig {
  return loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN, LOCAL_STORAGE_ROOT: root });
}

function makeEnvelope(
  jobType = 'content_generation',
  payload: Record<string, unknown> = { content_pack: 'release_pack' },
): JobEnvelope {
  return {
    job_id: 'job-bg',
    workspace_id: 'ws-bg',
    request_id: 'req-bg',
    job_type: jobType,
    callback_url: 'http://callback.test/cb',
    entity: { type: 'content_pack_request', id: 'ent-bg' },
    payload_version: '1.0',
    payload,
  };
}

function authHeaders(body: JobEnvelope) {
  return {
    'X-Internal-Token': TOKEN,
    'X-Workspace-ID': body.workspace_id,
    'X-Job-ID': body.job_id,
    'X-Request-ID': body.request_id,
  };
}

function recordingCallback() {
  const calls: { url: string; payload: CallbackPayload }[] = [];
  const client: CallbackClient = {
    send: async (url, payload) => {
      calls.push({ url, payload });
      return { ok: true, statusCode: 200 };
    },
  };
  return { client, calls };
}

/** Storage whose saveBuffer always fails — forces every output to fail. */
function failingStorage(real: LocalStorage): LocalStorage {
  return {
    name: real.name,
    root: real.root,
    buildStorageKey: (ws, job, file) => real.buildStorageKey(ws, job, file),
    resolveWithinRoot: (rel) => real.resolveWithinRoot(rel),
    getPublicUrl: (key) => real.getPublicUrl(key),
    saveBuffer: async (input: SaveBufferInput) => {
      throw new StorageFailedError('forced storage failure', { file_name: input.fileName });
    },
  };
}

describe('POST /jobs — background execution (R-HARD-001)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-bg-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('responds 202 BEFORE the callback is delivered', async () => {
    // The callback blocks on a gate the test controls; if the 202 waited for the
    // callback, the request would hang. Proving the 202 returns while the
    // callback is still pending demonstrates the background decoupling.
    const gate = createDeferred<void>();
    let callbackResolved = false;
    const client: CallbackClient = {
      send: async () => {
        await gate.promise;
        callbackResolved = true;
        return { ok: true, statusCode: 200 };
      },
    };
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope();

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);
    expect(res.body).toMatchObject({ status: 'accepted', job_id: 'job-bg' });
    // The 202 did NOT wait for the callback (still gated).
    expect(callbackResolved).toBe(false);

    // Release the gate and let the background task finish cleanly.
    gate.resolve();
    await waitUntil(() => callbackResolved);
  });

  it('delivers a completed callback in the background', async () => {
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope();

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);
    expect(res.status).toBe(202);
    // Nothing delivered synchronously with the 202.
    expect(calls).toHaveLength(0);

    await waitUntil(() => calls.length >= 1);
    expect(calls[0].url).toBe(body.callback_url);
    expect(calls[0].payload.status).toBe('completed');
    expect(calls[0].payload.job_id).toBe('job-bg');
  });

  it('delivers a failed callback in the background when the render fails', async () => {
    const { client, calls } = recordingCallback();
    const realStorage = createLocalStorage(configFor(root));
    const app = createApp(configFor(root), {
      logger: silentLogger,
      callbackClient: client,
      storage: failingStorage(realStorage),
    });
    const body = makeEnvelope();

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);
    expect(res.status).toBe(202);

    await waitUntil(() => calls.length >= 1);
    expect(calls[0].payload.status).toBe('failed');
    expect(calls[0].payload.result).toBeNull();
    expect(calls[0].payload.error).toMatchObject({ code: 'render_failed' });
  });

  it('does not crash the process when the callback delivery throws', async () => {
    const lines: string[] = [];
    const logger = createLogger({ write: (line) => lines.push(line) });
    const throwingClient: CallbackClient = {
      send: async () => {
        throw new CallbackFailedError('django is down');
      },
    };
    const app = createApp(configFor(root), { logger, callbackClient: throwingClient });
    const body = makeEnvelope();

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);
    expect(res.status).toBe(202);

    // The background task logs callback.failed and survives.
    await waitUntil(() => lines.join('\n').includes('callback.failed'));
    expect(lines.join('\n')).not.toContain('job.execution_failed');

    // The process is still alive: a second job is accepted and served normally.
    const res2 = await request(app).post('/jobs').set(authHeaders(body)).send(body);
    expect(res2.status).toBe(202);
  });
});

describe('scheduleJobExecution — global safety net (RSK-HARD-001)', () => {
  it('logs job.execution_failed and stays alive on an unexpected background error', async () => {
    // A faulty log sink throws while the renderer error is being logged. This
    // escapes executeJob's render try/catch and is only caught by the background
    // safety net — which must log job.execution_failed and never crash.
    const lines: string[] = [];
    const faultyLogger = createLogger({
      write: (line) => {
        if (line.includes('render.failed')) {
          throw new Error('log sink boom');
        }
        lines.push(line);
      },
    });
    const throwingRenderer: Renderer = async () => {
      throw new RenderFailedError('explode');
    };
    const { client, calls } = recordingCallback();
    const service = createJobService({
      config: loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN }),
      logger: faultyLogger,
      storage: createLocalStorage(loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN })),
      callbackClient: client,
      renderers: { content_generation: throwingRenderer },
    });

    service.scheduleJobExecution(makeEnvelope());

    // The safety net logged the unexpected failure...
    await waitUntil(() => lines.join('\n').includes('job.execution_failed'));
    // ...and still attempted a best-effort failed callback.
    await waitUntil(() => calls.length >= 1);
    expect(calls[0].payload.status).toBe('failed');
    // The token never appears in any log line.
    expect(lines.join('\n')).not.toContain(TOKEN);
  });
});
