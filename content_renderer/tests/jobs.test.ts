import { mkdtempSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { describe, expect, it } from 'vitest';
import request from 'supertest';

import { createApp } from '../src/app';
import type { CallbackClient } from '../src/callbacks/callback.client';
import { loadConfig } from '../src/config/env';
import type { CallbackPayload } from '../src/jobs/job.types';
import { createLogger } from '../src/logging/logger';
import { waitUntil } from './helpers';

const TOKEN = 'test-internal-token';

function buildApp() {
  // Real rendering now writes PNGs to storage; isolate them under a temp root.
  const root = mkdtempSync(path.join(os.tmpdir(), 'cr-jobs-'));
  const config = loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN, LOCAL_STORAGE_ROOT: root });
  // Silent logger keeps test output clean.
  const logger = createLogger({ write: () => {} });
  // Mock callback: never call the real Backend Core from tests.
  const callbackClient: CallbackClient = { send: async () => ({ ok: true, statusCode: 200 }) };
  return createApp(config, { logger, callbackClient });
}

/** App wired with a recording callback so background delivery can be asserted. */
function buildRecordingApp() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'cr-jobs-'));
  const config = loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN, LOCAL_STORAGE_ROOT: root });
  const logger = createLogger({ write: () => {} });
  const calls: { url: string; payload: CallbackPayload }[] = [];
  const callbackClient: CallbackClient = {
    send: async (url, payload) => {
      calls.push({ url, payload });
      return { ok: true, statusCode: 200 };
    },
  };
  return { app: createApp(config, { logger, callbackClient }), calls };
}

interface EnvelopeOverrides {
  job_id?: string;
  workspace_id?: string;
  request_id?: string;
  job_type?: string;
  callback_url?: string;
  entity?: { type: string; id: string };
  payload_version?: string;
  payload?: Record<string, unknown>;
}

function makeEnvelope(overrides: EnvelopeOverrides = {}) {
  return {
    job_id: 'job-123',
    workspace_id: 'ws-123',
    request_id: 'req-123',
    job_type: 'content_generation',
    callback_url: 'http://localhost:8100/api/v1/internal/jobs/callback/',
    entity: { type: 'content_pack_request', id: 'ent-123' },
    payload_version: '1.0',
    payload: {},
    ...overrides,
  };
}

function authHeaders(body: { workspace_id: string; job_id: string; request_id: string }) {
  return {
    'X-Internal-Token': TOKEN,
    'X-Workspace-ID': body.workspace_id,
    'X-Job-ID': body.job_id,
    'X-Request-ID': body.request_id,
  };
}

describe('POST /jobs — authentication', () => {
  it('rejects a request without X-Internal-Token (403)', async () => {
    const body = makeEnvelope();
    const res = await request(buildApp()).post('/jobs').send(body);

    expect(res.status).toBe(403);
    expect(res.body.error).toMatchObject({ code: 'unauthorized' });
    // The token must never leak into responses.
    expect(JSON.stringify(res.body)).not.toContain(TOKEN);
  });

  it('rejects a request with the wrong token (403)', async () => {
    const body = makeEnvelope();
    const res = await request(buildApp())
      .post('/jobs')
      .set({ ...authHeaders(body), 'X-Internal-Token': 'wrong-token' })
      .send(body);

    expect(res.status).toBe(403);
    expect(res.body.error).toMatchObject({ code: 'unauthorized' });
    expect(JSON.stringify(res.body)).not.toContain(TOKEN);
  });

  it('accepts a request with the correct token (202)', async () => {
    const body = makeEnvelope();
    const res = await request(buildApp()).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);
    expect(res.body).toMatchObject({ status: 'accepted', job_type: 'content_generation' });
  });
});

describe('POST /jobs — validation', () => {
  it('returns 400 for an invalid payload (missing field)', async () => {
    const body: Record<string, unknown> = makeEnvelope();
    // Remove a required field to make the envelope invalid.
    delete body.callback_url;

    const res = await request(buildApp())
      .post('/jobs')
      .set({
        'X-Internal-Token': TOKEN,
        'X-Workspace-ID': body.workspace_id as string,
        'X-Job-ID': body.job_id as string,
        'X-Request-ID': body.request_id as string,
      })
      .send(body);

    expect(res.status).toBe(400);
    expect(res.body.error).toMatchObject({ code: 'invalid_payload' });
    expect(Array.isArray(res.body.error.details.issues)).toBe(true);
  });

  it('returns 400 on X-Workspace-ID / body mismatch', async () => {
    const body = makeEnvelope();
    const res = await request(buildApp())
      .post('/jobs')
      .set({ ...authHeaders(body), 'X-Workspace-ID': 'different-workspace' })
      .send(body);

    expect(res.status).toBe(400);
    expect(res.body.error).toMatchObject({ code: 'bad_request' });
  });

  it('returns 400 on X-Job-ID / body mismatch', async () => {
    const body = makeEnvelope();
    const res = await request(buildApp())
      .post('/jobs')
      .set({ ...authHeaders(body), 'X-Job-ID': 'different-job' })
      .send(body);

    expect(res.status).toBe(400);
    expect(res.body.error).toMatchObject({ code: 'bad_request' });
  });

  it('returns 400 for an unsupported job_type', async () => {
    const body = makeEnvelope({ job_type: 'video_rendering' });
    const res = await request(buildApp()).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(400);
    expect(res.body.error).toMatchObject({ code: 'unsupported_job_type' });
  });
});

describe('POST /jobs — dispatcher (background execution)', () => {
  // The 202 no longer carries the render result; it is delivered to Django via
  // the callback on a later tick. Each test asserts the 202 acknowledgement and
  // then waits for the background callback before inspecting its payload.
  it('dispatches content_generation and calls back with a post output', async () => {
    const { app, calls } = buildRecordingApp();
    const body = makeEnvelope({ job_type: 'content_generation' });
    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);
    expect(res.body).toMatchObject({ status: 'accepted', job_type: 'content_generation' });
    // The result is NOT echoed synchronously in the 202 body.
    expect(res.body.result).toBeUndefined();

    await waitUntil(() => calls.length >= 1);
    expect(calls[0].payload.status).toBe('completed');
    expect(calls[0].payload.result?.outputs?.[0].output_type).toBe('post');
  });

  it('dispatches report_generation and calls back with a report asset', async () => {
    const { app, calls } = buildRecordingApp();
    const body = makeEnvelope({
      job_type: 'report_generation',
      entity: { type: 'report', id: 'rep-123' },
      payload: { report_type: 'weekly_growth', title: 'Weekly Report' },
    });
    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);
    expect(res.body.job_type).toBe('report_generation');

    await waitUntil(() => calls.length >= 1);
    expect(calls[0].payload.status).toBe('completed');
    // Report uses the single-asset result shape Django reads (result.asset).
    expect(calls[0].payload.result?.asset?.format).toBe('pdf');
  });

  it('dispatches media_kit_generation and calls back with a media_kit asset', async () => {
    const { app, calls } = buildRecordingApp();
    const body = makeEnvelope({
      job_type: 'media_kit_generation',
      entity: { type: 'media_kit', id: 'mk-123' },
      payload: { artist: { name: 'Nova' } },
    });
    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);
    expect(res.body.job_type).toBe('media_kit_generation');

    await waitUntil(() => calls.length >= 1);
    expect(calls[0].payload.status).toBe('completed');
    expect(calls[0].payload.result?.asset?.format).toBe('pdf');
  });
});
