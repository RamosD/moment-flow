import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';

import { createApp } from '../src/app';
import { buildFailedPayload } from '../src/callbacks/callback.payload';
import type { CallbackClient } from '../src/callbacks/callback.client';
import { loadConfig, type AppConfig } from '../src/config/env';
import {
  CallbackFailedError,
  InvalidPayloadError,
  RenderFailedError,
  StorageFailedError,
  TimeoutError,
  UnsupportedJobTypeError,
  UnsupportedTemplateError,
} from '../src/errors/errors';
import { createJobService } from '../src/jobs/job.service';
import type { JobEnvelope } from '../src/jobs/job.types';
import { withTimeout } from '../src/jobs/with-timeout';
import { createLogger } from '../src/logging/logger';
import type { Renderer } from '../src/renderers/renderer.types';
import { createLocalStorage, type LocalStorage } from '../src/storage/local-storage';
import { waitUntil } from './helpers';

const TOKEN = 'test-internal-token';
const silentLogger = createLogger({ write: () => {} });

function baseConfig(overrides: Partial<AppConfig> = {}): AppConfig {
  return { ...loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN }), ...overrides };
}

function configFor(root: string): AppConfig {
  return loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN, LOCAL_STORAGE_ROOT: root });
}

/** A storage stub for dispatcher tests whose renderers don't touch storage. */
const stubStorage: LocalStorage = {
  name: 'local',
  root: '/tmp/unused',
  buildStorageKey: (ws, job, file) => `workspaces/${ws}/jobs/${job}/${file}`,
  resolveWithinRoot: () => null,
  getPublicUrl: (key) => `http://localhost/files/${key}`,
  saveBuffer: async () => {
    throw new Error('storage should not be used in this test');
  },
};

function recordingCallback() {
  const calls: { url: string; payload: ReturnType<typeof buildFailedPayload> }[] = [];
  const client: CallbackClient = {
    send: async (url, payload) => {
      calls.push({ url, payload });
      return { ok: true, statusCode: 200 };
    },
  };
  return { client, calls };
}

function makeEnvelope(jobType: string, payload: Record<string, unknown> = {}): JobEnvelope {
  return {
    job_id: 'job-h',
    workspace_id: 'ws-h',
    request_id: 'req-h',
    job_type: jobType,
    callback_url: 'http://callback.test/cb',
    entity: { type: 'content_pack_request', id: 'ent-h' },
    payload_version: '1.0',
    payload,
  };
}

describe('error normalization', () => {
  it('every render error carries a stable code, status and a {code,message,details} body', () => {
    const cases: Array<[Error & { code: string; statusCode: number; toJSON: () => unknown }, string, number]> = [
      [new InvalidPayloadError(), 'invalid_payload', 400],
      [new UnsupportedJobTypeError('video_rendering'), 'unsupported_job_type', 400],
      [new UnsupportedTemplateError('weird_template'), 'unsupported_template', 422],
      [new RenderFailedError(), 'render_failed', 500],
      [new StorageFailedError(), 'storage_failed', 500],
      [new CallbackFailedError(), 'callback_failed', 502],
      [new TimeoutError(), 'timeout', 504],
    ];

    for (const [error, code, status] of cases) {
      expect(error.code).toBe(code);
      expect(error.statusCode).toBe(status);
      const json = error.toJSON() as Record<string, unknown>;
      expect(Object.keys(json).sort()).toEqual(['code', 'details', 'message']);
      expect(json.code).toBe(code);
      expect(typeof json.message).toBe('string');
    }
  });
});

describe('failed callback details never leak secrets', () => {
  it('redacts token/secret-shaped keys in error.details (defence-in-depth)', () => {
    const payload = buildFailedPayload(makeEnvelope('content_generation'), {
      code: 'render_failed',
      message: 'boom',
      details: {
        internal_api_token: 'SUPER-SECRET-TOKEN',
        nested: { authorization: 'Bearer SUPER-SECRET-TOKEN', api_key: 'k' },
        safe: 'keep-me',
      },
    });

    const serialized = JSON.stringify(payload);
    expect(serialized).not.toContain('SUPER-SECRET-TOKEN');
    const details = payload.error!.details as Record<string, unknown>;
    expect(details.internal_api_token).toBe('[REDACTED]');
    expect(details.safe).toBe('keep-me');
    expect((details.nested as Record<string, unknown>).authorization).toBe('[REDACTED]');
  });
});

describe('withTimeout', () => {
  it('resolves when the operation is fast enough', async () => {
    await expect(withTimeout(Promise.resolve('ok'), 1000)).resolves.toBe('ok');
  });

  it('rejects with a normalised TimeoutError when too slow', async () => {
    const slow = new Promise((resolve) => setTimeout(() => resolve('late'), 100));
    await expect(withTimeout(slow, 20, { operation: 'render' })).rejects.toBeInstanceOf(TimeoutError);
  });
});

describe('dispatcher robustness (callback contract)', () => {
  it('unsupported job_type throws and sends NO callback', async () => {
    const { client, calls } = recordingCallback();
    const service = createJobService({
      config: baseConfig(),
      logger: silentLogger,
      storage: stubStorage,
      callbackClient: client,
    });

    // Reception gate is synchronous: an unsupported job_type is declined up-front
    // (controller → 400) and is never scheduled, so no callback is ever sent.
    expect(() => service.acceptJob(makeEnvelope('video_rendering'))).toThrow(UnsupportedJobTypeError);
    expect(calls).toHaveLength(0);
  });

  it('a render timeout produces a failed callback with code "timeout"', async () => {
    const slowRenderer: Renderer = () =>
      new Promise((resolve) => setTimeout(() => resolve({ status: 'completed', outputs: [] }), 120));
    const { client, calls } = recordingCallback();
    const service = createJobService({
      config: baseConfig({ renderTimeoutSeconds: 0.02 }),
      logger: silentLogger,
      storage: stubStorage,
      callbackClient: client,
      renderers: { content_generation: slowRenderer },
    });

    const result = await service.executeJob(makeEnvelope('content_generation'));

    expect(result.status).toBe('failed');
    expect(calls).toHaveLength(1);
    expect(calls[0].payload.status).toBe('failed');
    expect(calls[0].payload.error).toMatchObject({ code: 'timeout' });
  });

  it('a thrown render error produces a failed callback (code preserved)', async () => {
    const throwingRenderer: Renderer = async () => {
      throw new RenderFailedError('explode');
    };
    const { client, calls } = recordingCallback();
    const service = createJobService({
      config: baseConfig(),
      logger: silentLogger,
      storage: stubStorage,
      callbackClient: client,
      renderers: { content_generation: throwingRenderer },
    });

    const result = await service.executeJob(makeEnvelope('content_generation'));

    expect(result.status).toBe('failed');
    expect(calls[0].payload.error).toMatchObject({ code: 'render_failed' });
  });

  it('a storage-failed output is reported as render_failed with first_error in details', async () => {
    const storageFailRenderer: Renderer = async () => ({
      status: 'failed',
      outputs: [
        {
          output_type: 'post',
          format: 'png',
          status: 'failed',
          required: true,
          metadata: { error: { code: 'storage_failed', message: 'disk full' } },
        },
      ],
    });
    const { client, calls } = recordingCallback();
    const service = createJobService({
      config: baseConfig(),
      logger: silentLogger,
      storage: stubStorage,
      callbackClient: client,
      renderers: { content_generation: storageFailRenderer },
    });

    await service.executeJob(makeEnvelope('content_generation'));

    expect(calls[0].payload.error).toMatchObject({ code: 'render_failed' });
    expect(calls[0].payload.error?.details).toMatchObject({
      first_error: { code: 'storage_failed' },
    });
  });

  it('partial success forwards partially_completed with both outputs and no top-level error', async () => {
    const partialRenderer: Renderer = async () => ({
      status: 'partially_completed',
      outputs: [
        { output_type: 'post', format: 'png', status: 'completed', required: true },
        { output_type: 'story', format: 'png', status: 'failed', required: false, metadata: { error: { code: 'render_failed', message: 'x' } } },
      ],
    });
    const { client, calls } = recordingCallback();
    const service = createJobService({
      config: baseConfig(),
      logger: silentLogger,
      storage: stubStorage,
      callbackClient: client,
      renderers: { content_generation: partialRenderer },
    });

    const result = await service.executeJob(makeEnvelope('content_generation'));

    expect(result.status).toBe('partially_completed');
    expect(calls[0].payload.status).toBe('partially_completed');
    expect(calls[0].payload.error).toBeNull();
    expect(calls[0].payload.result?.outputs).toHaveLength(2);
  });

  it('a callback delivery failure is non-fatal and logged', async () => {
    const okRenderer: Renderer = async () => ({ status: 'completed', outputs: [] });
    const failingClient: CallbackClient = {
      send: async () => {
        throw new CallbackFailedError();
      },
    };
    const lines: string[] = [];
    const service = createJobService({
      config: baseConfig(),
      logger: createLogger({ write: (line) => lines.push(line) }),
      storage: stubStorage,
      callbackClient: failingClient,
      renderers: { content_generation: okRenderer },
    });

    const result = await service.executeJob(makeEnvelope('content_generation'));

    // The job itself is not failed by a callback delivery problem.
    expect(result.status).toBe('completed');
    expect(lines.join('\n')).toContain('callback.failed');
  });
});

describe('lifecycle logs (full POST /jobs) never expose the token', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-hard-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('emits accepted/scheduled/started/completed/callback events and no token', async () => {
    const lines: string[] = [];
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), {
      logger: createLogger({ write: (line) => lines.push(line) }),
      callbackClient: client,
    });
    const body = makeEnvelope('content_generation', { content_pack: 'release_pack' });

    const res = await request(app)
      .post('/jobs')
      .set({
        'X-Internal-Token': TOKEN,
        'X-Workspace-ID': body.workspace_id,
        'X-Job-ID': body.job_id,
        'X-Request-ID': body.request_id,
      })
      .send(body);

    expect(res.status).toBe(202);

    // Render + callback run in the background; wait for delivery before asserting
    // on the lifecycle logs.
    await waitUntil(() => calls.length >= 1);

    const output = lines.join('\n');
    for (const event of [
      'job.accepted',
      'job.scheduled',
      'render.started',
      'render.completed',
      'callback.started',
      'callback.completed',
    ]) {
      expect(output).toContain(event);
    }
    // The internal token must never be written to logs.
    expect(output).not.toContain(TOKEN);
    // Correlation ids are present.
    expect(output).toContain('"job_id":"job-h"');
    expect(output).toContain('"job_type":"content_generation"');
    expect(output).toContain('"request_id":"req-h"');
  });
});

describe('path traversal stays blocked', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-hard-st-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('rejects unsafe segments and paths escaping the storage root', async () => {
    const storage = createLocalStorage(configFor(root));

    expect(storage.resolveWithinRoot('../../etc/passwd')).toBeNull();
    await expect(
      storage.saveBuffer({ workspaceId: '..', jobId: 'job', fileName: 'f.png', data: Buffer.from('x') }),
    ).rejects.toBeInstanceOf(StorageFailedError);
    await expect(
      storage.saveBuffer({ workspaceId: 'ws', jobId: 'job', fileName: '../escape.png', data: Buffer.from('x') }),
    ).rejects.toBeInstanceOf(StorageFailedError);
  });
});
