import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';

import { createApp } from '../src/app';
import type { CallbackClient } from '../src/callbacks/callback.client';
import { loadConfig, type AppConfig } from '../src/config/env';
import { StorageFailedError } from '../src/errors/errors';
import type { CallbackPayload, JobEnvelope } from '../src/jobs/job.types';
import { createLogger } from '../src/logging/logger';
import { renderContentGeneration } from '../src/renderers/content';
import type { RenderContext } from '../src/renderers/renderer.types';
import { createLocalStorage, type LocalStorage, type SaveBufferInput } from '../src/storage/local-storage';
import { waitUntil } from './helpers';

const TOKEN = 'test-internal-token';
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

const silentLogger = createLogger({ write: () => {} });

function configFor(root: string): AppConfig {
  return loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN, LOCAL_STORAGE_ROOT: root });
}

function makeEnvelope(
  payload: Record<string, unknown>,
  overrides: Partial<JobEnvelope> = {},
): JobEnvelope {
  return {
    job_id: 'job-abc',
    workspace_id: 'ws-abc',
    request_id: 'req-abc',
    job_type: 'content_generation',
    callback_url: 'http://callback.test/cb',
    entity: { type: 'content_pack_request', id: 'ent-abc' },
    payload_version: '1.0',
    payload,
    ...overrides,
  };
}

/** A storage decorator whose saveBuffer fails for file names matched by `fails`. */
function failingStorage(real: LocalStorage, fails: (fileName: string) => boolean): LocalStorage {
  return {
    name: real.name,
    root: real.root,
    buildStorageKey: (ws, job, file) => real.buildStorageKey(ws, job, file),
    resolveWithinRoot: (rel) => real.resolveWithinRoot(rel),
    getPublicUrl: (key) => real.getPublicUrl(key),
    saveBuffer: async (input: SaveBufferInput) => {
      if (fails(input.fileName)) {
        throw new StorageFailedError('forced storage failure', { file_name: input.fileName });
      }
      return real.saveBuffer(input);
    },
  };
}

describe('content_generation renderer — unit', () => {
  let root: string;
  let storage: LocalStorage;
  let context: RenderContext;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-content-'));
    storage = createLocalStorage(configFor(root));
    context = { config: configFor(root), logger: silentLogger, storage };
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('generates at least one real PNG and persists it to local storage', async () => {
    const envelope = makeEnvelope({
      artist: { name: 'Nova' },
      track: { title: 'Midnight' },
    });

    const result = await renderContentGeneration(envelope, context);

    expect(result.status).toBe('completed');
    expect(result.outputs.length).toBeGreaterThanOrEqual(1);

    const output = result.outputs[0];
    expect(output.status).toBe('completed');
    expect(output.format).toBe('png');
    expect(output.asset?.mime_type).toBe('image/png');

    // The file really exists on disk and is a real PNG.
    const onDisk = path.join(root, ...output.asset!.storage_key.split('/'));
    const bytes = await readFile(onDisk);
    expect(bytes.length).toBeGreaterThan(0);
    expect(bytes.subarray(0, 8).equals(PNG_SIGNATURE)).toBe(true);
  });

  it('produces Django-compatible asset metadata', async () => {
    const result = await renderContentGeneration(makeEnvelope({}), context);
    const asset = result.outputs[0].asset!;

    expect(asset).toMatchObject({
      storage_provider: 'local',
      bucket: '',
      mime_type: 'image/png',
      width: 1080,
      height: 1080,
      duration_seconds: null,
    });
    expect(asset.storage_key).toMatch(/^workspaces\/ws-abc\/jobs\/job-abc\/output_\d{3}\.png$/);
    expect(asset.file_name).toMatch(/^output_\d{3}\.png$/);
    expect(asset.file_size_bytes).toBeGreaterThan(0);
    expect(asset.checksum).toMatch(/^[a-f0-9]{64}$/);
  });

  it('renders a release_pack card with the release template', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ content_pack: { type: 'release_pack' }, track: { title: 'Sunrise' } }),
      context,
    );
    expect(result.status).toBe('completed');
    expect(result.outputs[0].template_key).toBe('release_card');
    expect(result.outputs[0].metadata?.content_pack).toBe('release_pack');
  });

  it('renders a milestone_pack card with the milestone template', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ content_pack: 'milestone_pack', metric: '1,000,000 streams' }),
      context,
    );
    expect(result.status).toBe('completed');
    expect(result.outputs[0].template_key).toBe('milestone_card');
  });

  it('renders a weekly_growth_pack card with the weekly template', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ content_pack: { key: 'weekly_growth_pack' } }),
      context,
    );
    expect(result.status).toBe('completed');
    expect(result.outputs[0].template_key).toBe('weekly_growth_card');
  });

  it('renders a monthly_recap_pack card', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ content_pack: 'monthly_recap_pack' }),
      context,
    );
    expect(result.status).toBe('completed');
    expect(result.outputs[0].status).toBe('completed');
  });

  it('falls back to a generic post for an unknown content pack', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ content_pack: 'totally_unknown_pack' }),
      context,
    );
    expect(result.status).toBe('completed');
    expect(result.outputs[0].template_key).toBe('generic_post');
    expect(result.outputs[0].metadata?.content_pack).toBe('totally_unknown_pack');
  });

  it('generates a fallback output when expected_outputs is empty and no pack is given', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ expected_outputs: [] }),
      context,
    );
    expect(result.status).toBe('completed');
    expect(result.outputs).toHaveLength(1);
    expect(result.outputs[0].output_type).toBe('post');
  });

  it('selects the template and resolves the dimension from each expected_output', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({
        expected_outputs: [
          {
            output_type: 'story',
            template_key: 'generic_story',
            format: 'story_9_16',
            required: true,
            title: 'My Story',
            caption: 'A caption',
            cta: 'Tap to listen',
          },
        ],
      }),
      context,
    );

    const output = result.outputs[0];
    expect(output.output_type).toBe('story');
    expect(output.template_key).toBe('generic_story');
    expect(output.title).toBe('My Story');
    expect(output.caption).toBe('A caption');
    expect(output.cta).toBe('Tap to listen');
    expect(output.asset).toMatchObject({ width: 1080, height: 1920 });
    expect(output.metadata?.dimension).toBe('story_9_16');
  });

  it('supports partial success: one output succeeds, another fails', async () => {
    // Fail only the second file; the first one still renders and persists.
    context = {
      config: configFor(root),
      logger: silentLogger,
      storage: failingStorage(storage, (name) => name === 'output_002.png'),
    };

    const result = await renderContentGeneration(
      makeEnvelope({
        expected_outputs: [
          { output_type: 'post', template_key: 'release_card', required: true },
          { output_type: 'story', template_key: 'generic_story', required: false },
        ],
      }),
      context,
    );

    expect(result.status).toBe('partially_completed');
    expect(result.outputs).toHaveLength(2);
    expect(result.outputs[0].status).toBe('completed');
    expect(result.outputs[0].asset).toBeDefined();
    expect(result.outputs[1].status).toBe('failed');
    expect(result.outputs[1].asset).toBeUndefined();
    // Failed outputs carry safe error metadata (code + message, no secrets/stack).
    expect(result.outputs[1].metadata?.error).toMatchObject({ code: 'storage_failed' });
  });

  it('reports status "failed" when every output fails', async () => {
    context = {
      config: configFor(root),
      logger: silentLogger,
      storage: failingStorage(storage, () => true),
    };

    const result = await renderContentGeneration(makeEnvelope({ content_pack: 'release_pack' }), context);

    expect(result.status).toBe('failed');
    expect(result.outputs.every((o) => o.status === 'failed')).toBe(true);
  });
});

// --- Template echo / resolution metadata (R-HARD-004) ------------------------

describe('content_generation renderer — template echo (R-HARD-004)', () => {
  let root: string;
  let context: RenderContext;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-content-tpl-'));
    context = { config: configFor(root), logger: silentLogger, storage: createLocalStorage(configFor(root)) };
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  const SENSITIVE_KEY = /token|secret|password|authorization|api[-_]?key|credential/i;

  it('preserves a valid requested template_key (top-level + resolution metadata)', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ expected_outputs: [{ output_type: 'post', template_key: 'release_card' }] }),
      context,
    );

    const out = result.outputs[0];
    expect(out.status).toBe('completed');
    expect(out.template_key).toBe('release_card');
    expect(out.metadata?.requested_template_key).toBe('release_card');
    expect(out.metadata?.resolved_template_key).toBe('release_card');
    expect(out.metadata?.used_fallback_template).toBe(false);
    expect(out.metadata?.dimension).toBe('post_1_1');
    expect(out.metadata?.width).toBe(1080);
    expect(out.metadata?.height).toBe(1080);
  });

  it('echoes template_id when provided in an expected_output (never inventing it)', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({
        expected_outputs: [
          { output_type: 'post', template_key: 'release_card', template_id: 'tmpl-uuid-123' },
        ],
      }),
      context,
    );

    const out = result.outputs[0];
    expect(out.template_id).toBe('tmpl-uuid-123');
    expect(out.metadata?.requested_template_id).toBe('tmpl-uuid-123');
  });

  it('preserves a template_id provided via the payload templates[] override', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({
        templates: [{ template_key: 'release_card', template_id: 'tmpl-from-templates' }],
        expected_outputs: [{ output_type: 'post', template_key: 'release_card' }],
      }),
      context,
    );

    expect(result.outputs[0].template_id).toBe('tmpl-from-templates');
  });

  it('makes an unknown template fallback explicit', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ expected_outputs: [{ output_type: 'post', template_key: 'does_not_exist' }] }),
      context,
    );

    const out = result.outputs[0];
    // Top-level key is the resolved (compatible) value, not the unknown request.
    expect(out.template_key).toBe('generic_post');
    expect(out.metadata?.requested_template_key).toBe('does_not_exist');
    expect(out.metadata?.resolved_template_key).toBe('generic_post');
    expect(out.metadata?.used_fallback_template).toBe(true);
  });

  it('makes an unknown format fallback explicit', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({
        expected_outputs: [{ output_type: 'post', template_key: 'generic_post', format: 'weird_format' }],
      }),
      context,
    );

    const out = result.outputs[0];
    expect(out.metadata?.used_fallback_format).toBe(true);
    expect(out.metadata?.dimension).toBe('post_1_1');
    expect(out.metadata?.width).toBe(1080);
    expect(out.metadata?.height).toBe(1080);
  });

  it('keeps outputs without a template_id valid (no invented id)', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ content_pack: 'release_pack' }),
      context,
    );

    const out = result.outputs[0];
    expect(out.status).toBe('completed');
    expect(out.template_id).toBeUndefined();
    expect(out.metadata).not.toHaveProperty('requested_template_id');
    expect(out.metadata?.resolved_template_key).toBe('release_card');
  });

  it('carries the echo fields on a failed output too', async () => {
    const failing: RenderContext = {
      config: configFor(root),
      logger: silentLogger,
      storage: failingStorage(createLocalStorage(configFor(root)), () => true),
    };
    const result = await renderContentGeneration(
      makeEnvelope({
        expected_outputs: [
          { output_type: 'post', template_key: 'unknown_card', template_id: 'tmpl-x' },
        ],
      }),
      failing,
    );

    const out = result.outputs[0];
    expect(out.status).toBe('failed');
    expect(out.template_key).toBe('generic_post');
    expect(out.template_id).toBe('tmpl-x');
    expect(out.metadata?.requested_template_key).toBe('unknown_card');
    expect(out.metadata?.resolved_template_key).toBe('generic_post');
    expect(out.metadata?.used_fallback_template).toBe(true);
  });

  it('does not place sensitive data in the resolution metadata', async () => {
    const result = await renderContentGeneration(
      makeEnvelope({ expected_outputs: [{ output_type: 'post', template_key: 'release_card' }] }),
      context,
    );

    const metadata = result.outputs[0].metadata ?? {};
    for (const key of Object.keys(metadata)) {
      expect(SENSITIVE_KEY.test(key)).toBe(false);
    }
    expect(JSON.stringify(metadata)).not.toContain(TOKEN);
  });
});

// --- Integration: full POST /jobs flow with a mocked (recording) callback -----

function recordingCallback(): { client: CallbackClient; calls: { url: string; payload: CallbackPayload }[] } {
  const calls: { url: string; payload: CallbackPayload }[] = [];
  const client: CallbackClient = {
    send: async (url, payload) => {
      calls.push({ url, payload });
      return { ok: true, statusCode: 200 };
    },
  };
  return { client, calls };
}

function authHeaders(body: JobEnvelope) {
  return {
    'X-Internal-Token': TOKEN,
    'X-Workspace-ID': body.workspace_id,
    'X-Job-ID': body.job_id,
    'X-Request-ID': body.request_id,
  };
}

describe('POST /jobs content_generation — integration (mocked callback)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-content-e2e-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('sends a completed callback with Django-compatible asset metadata and the file exists on disk', async () => {
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope({ content_pack: 'release_pack', track: { title: 'Aurora' } });

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);

    // Render + callback run in the background; wait for delivery before asserting.
    await waitUntil(() => calls.length >= 1);

    // A single callback was delivered, to the body's callback_url.
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe(body.callback_url);

    const payload = calls[0].payload;
    expect(payload).toMatchObject({
      job_id: 'job-abc',
      workspace_id: 'ws-abc',
      status: 'completed',
      error: null,
      entity: { type: 'content_pack_request', id: 'ent-abc' },
    });
    expect(payload.metadata).toMatchObject({
      renderer: 'content_renderer',
      renderer_version: '0.1.0',
    });

    // Content keeps the multi-output result shape (result.outputs[]).
    const asset = payload.result!.outputs![0].asset!;
    expect(asset).toMatchObject({
      storage_provider: 'local',
      bucket: '',
      mime_type: 'image/png',
      width: 1080,
      height: 1080,
      duration_seconds: null,
    });
    expect(asset.file_size_bytes).toBeGreaterThan(0);
    expect(asset.checksum).toMatch(/^[a-f0-9]{64}$/);

    // The asset really exists in local storage.
    const onDisk = path.join(root, ...asset.storage_key.split('/'));
    const bytes = await readFile(onDisk);
    expect(bytes.subarray(0, 8).equals(PNG_SIGNATURE)).toBe(true);
  });

  it('sends a failed callback when every output fails to render', async () => {
    const { client, calls } = recordingCallback();
    const realStorage = createLocalStorage(configFor(root));
    const app = createApp(configFor(root), {
      logger: silentLogger,
      callbackClient: client,
      storage: failingStorage(realStorage, () => true),
    });
    const body = makeEnvelope({ content_pack: 'release_pack' });

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);

    await waitUntil(() => calls.length >= 1);
    expect(calls).toHaveLength(1);
    const payload = calls[0].payload;
    expect(payload.status).toBe('failed');
    expect(payload.result).toBeNull();
    expect(payload.error).toMatchObject({ code: 'render_failed', message: 'Falha ao gerar o conteúdo.' });
    expect(payload.error?.details).toMatchObject({ outputs_failed: 1 });
  });

  it('callback output carries template_key/template_id and resolution metadata', async () => {
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope({
      expected_outputs: [
        { output_type: 'post', template_key: 'release_card', template_id: 'tmpl-cb-1' },
      ],
    });

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);
    expect(res.status).toBe(202);

    await waitUntil(() => calls.length >= 1);
    const output = calls[0].payload.result!.outputs![0];
    // Backwards-compatible: existing fields stay; new ones are additive.
    expect(output.template_key).toBe('release_card');
    expect(output.template_id).toBe('tmpl-cb-1');
    expect(output.metadata).toMatchObject({
      requested_template_key: 'release_card',
      requested_template_id: 'tmpl-cb-1',
      resolved_template_key: 'release_card',
      used_fallback_template: false,
      used_fallback_format: false,
    });
  });
});
