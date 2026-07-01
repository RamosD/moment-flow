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
import { renderMediaKitGeneration } from '../src/renderers/media-kits';
import { renderMediaKitHtml } from '../src/renderers/media-kits/media-kit.html';
import {
  buildMediaKitModel,
  parseMediaKitPayload,
} from '../src/renderers/media-kits/media-kit.model';
import type { RenderContext } from '../src/renderers/renderer.types';
import {
  createLocalStorage,
  type LocalStorage,
  type SaveBufferInput,
} from '../src/storage/local-storage';
import { waitUntil } from './helpers';

const TOKEN = 'test-internal-token';
const PDF_SIGNATURE = '%PDF-';
const silentLogger = createLogger({ write: () => {} });

function configFor(root: string, overrides: NodeJS.ProcessEnv = {}): AppConfig {
  return loadConfig({
    NODE_ENV: 'test',
    INTERNAL_API_TOKEN: TOKEN,
    LOCAL_STORAGE_ROOT: root,
    ...overrides,
  });
}

const MINIMAL_PAYLOAD = { artist: { name: 'Nova' } };

const RICH_PAYLOAD = {
  artist: {
    name: 'Nova',
    tagline: 'Synthwave from Lisbon',
    bio: 'Nova is an electronic artist blending retro synths with modern pop.',
    contact: { email: 'team@nova.fm', management: 'Bright Artists' },
    links: { instagram: 'https://instagram.com/nova', spotify: 'https://open.spotify.com/nova' },
  },
  campaign: { name: 'Summer Push' },
  track: { title: 'Midnight Drive' },
  items: [
    'Featured on New Music Friday',
    { title: '1M streams', description: 'in the first month' },
  ],
  assets: [
    { file_name: 'press_photo.jpg', type: 'image/jpeg' },
    { file_name: 'logo.png', type: 'image/png' },
  ],
  smart_links: [{ label: 'Listen', url: 'https://chartrex.link/midnight' }],
  branding: { brand_color: '#0984E3' },
};

function makeEnvelope(
  payload: Record<string, unknown>,
  overrides: Partial<JobEnvelope> = {},
): JobEnvelope {
  return {
    job_id: 'job-mk',
    workspace_id: 'ws-mk',
    request_id: 'req-mk',
    job_type: 'media_kit_generation',
    callback_url: 'http://callback.test/cb',
    entity: { type: 'media_kit', id: 'mk-1' },
    payload_version: '1.0',
    payload,
    ...overrides,
  };
}

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

describe('media kit model + html', () => {
  it('rejects a payload without an artist name', () => {
    expect(parseMediaKitPayload({}).success).toBe(false);
    expect(parseMediaKitPayload({ artist: {} }).success).toBe(false);
    expect(parseMediaKitPayload({ campaign: { name: 'x' } }).success).toBe(false);
  });

  it('accepts a minimal payload (artist name only)', () => {
    const parsed = parseMediaKitPayload(MINIMAL_PAYLOAD);
    expect(parsed.success).toBe(true);
    if (!parsed.success) return;
    const model = buildMediaKitModel(parsed.data);
    expect(model.artistName).toBe('Nova');
  });

  it('normalises a rich payload (items, assets, links, contacts)', () => {
    const parsed = parseMediaKitPayload(RICH_PAYLOAD);
    if (!parsed.success) throw new Error('expected valid payload');
    const model = buildMediaKitModel(parsed.data);

    expect(model.artistName).toBe('Nova');
    expect(model.tagline).toBe('Synthwave from Lisbon');
    expect(model.trackTitle).toBe('Midnight Drive');
    expect(model.campaignName).toBe('Summer Push');
    expect(model.highlights).toContain('Featured on New Music Friday');
    expect(model.highlights).toContain('1M streams — in the first month');
    expect(model.links.map((l) => l.url)).toContain('https://chartrex.link/midnight');
    expect(model.links.map((l) => l.url)).toContain('https://instagram.com/nova');
    expect(model.contacts.map((c) => c.value)).toContain('team@nova.fm');
    expect(model.assets.map((a) => a.label)).toContain('press_photo.jpg');
    expect(model.brandColor).toBe('#0984E3');
  });

  it('renders HTML with the media-kit data and a safe link', () => {
    const parsed = parseMediaKitPayload(RICH_PAYLOAD);
    if (!parsed.success) throw new Error('expected valid payload');
    const html = renderMediaKitHtml(buildMediaKitModel(parsed.data));

    expect(html).toContain('<!DOCTYPE html>');
    for (const text of ['Nova', 'Synthwave from Lisbon', 'Midnight Drive', 'Highlights', 'Listen']) {
      expect(html).toContain(text);
    }
    expect(html).toContain('href="https://chartrex.link/midnight"');
  });

  it('does not emit a javascript: link', () => {
    const parsed = parseMediaKitPayload({
      artist: { name: 'X' },
      smart_links: [{ label: 'evil', url: 'javascript:alert(1)' }],
    });
    if (!parsed.success) throw new Error('expected valid payload');
    const html = renderMediaKitHtml(buildMediaKitModel(parsed.data));
    expect(html).not.toContain('href="javascript:');
  });
});

describe('media_kit_generation renderer — unit', () => {
  let root: string;
  let storage: LocalStorage;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-mk-'));
    storage = createLocalStorage(configFor(root));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('generates a PDF from a minimal payload and persists it', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderMediaKitGeneration(makeEnvelope(MINIMAL_PAYLOAD), context);

    expect(result.status).toBe('completed');
    const output = result.outputs[0];
    expect(output.output_type).toBe('media_kit');
    expect(output.format).toBe('pdf');
    expect(output.asset?.mime_type).toBe('application/pdf');

    const onDisk = path.join(root, ...output.asset!.storage_key.split('/'));
    const bytes = await readFile(onDisk);
    expect(bytes.length).toBeGreaterThan(0);
    expect(bytes.subarray(0, 5).toString('latin1')).toBe(PDF_SIGNATURE);
  });

  it('generates a PDF from a rich payload (items/assets/links)', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderMediaKitGeneration(makeEnvelope(RICH_PAYLOAD), context);

    expect(result.status).toBe('completed');
    expect(result.outputs[0].metadata?.highlight_count).toBe(2);
    expect(result.outputs[0].metadata?.asset_count).toBe(2);
    expect(result.outputs[0].metadata?.link_count).toBeGreaterThanOrEqual(1);
  });

  it('produces Django-compatible asset metadata', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderMediaKitGeneration(makeEnvelope(RICH_PAYLOAD), context);
    const asset = result.outputs[0].asset!;

    expect(asset).toMatchObject({
      storage_provider: 'local',
      bucket: '',
      file_name: 'media_kit.pdf',
      mime_type: 'application/pdf',
      width: null,
      height: null,
      duration_seconds: null,
    });
    expect(asset.storage_key).toBe('workspaces/ws-mk/jobs/job-mk/media_kit.pdf');
    expect(asset.file_size_bytes).toBeGreaterThan(0);
    expect(asset.checksum).toMatch(/^[a-f0-9]{64}$/);
  });

  it('falls back to HTML when REPORT_OUTPUT_FORMAT=html', async () => {
    const config = configFor(root, { REPORT_OUTPUT_FORMAT: 'html' });
    const context: RenderContext = { config, logger: silentLogger, storage };
    const result = await renderMediaKitGeneration(makeEnvelope(RICH_PAYLOAD), context);

    const output = result.outputs[0];
    expect(output.format).toBe('html');
    expect(output.metadata?.fallback_html).toBe(true);
    expect(output.asset?.mime_type).toBe('text/html');

    const onDisk = path.join(root, ...output.asset!.storage_key.split('/'));
    const html = await readFile(onDisk, 'utf8');
    expect(html).toContain('Nova');
  });

  it('returns a failed result for an invalid payload', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderMediaKitGeneration(makeEnvelope({}), context);

    expect(result.status).toBe('failed');
    expect(result.outputs[0].metadata?.error).toMatchObject({ code: 'invalid_payload' });
  });

  it('returns a failed result when storage fails', async () => {
    const context: RenderContext = {
      config: configFor(root),
      logger: silentLogger,
      storage: failingStorage(storage),
    };
    const result = await renderMediaKitGeneration(makeEnvelope(MINIMAL_PAYLOAD), context);

    expect(result.status).toBe('failed');
    expect(result.outputs[0].metadata?.error).toMatchObject({ code: 'storage_failed' });
  });
});

// --- Integration: full POST /jobs flow with a mocked (recording) callback -----

function recordingCallback(): {
  client: CallbackClient;
  calls: { url: string; payload: CallbackPayload }[];
} {
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

describe('POST /jobs media_kit_generation — integration (mocked callback)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-mk-e2e-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('sends a completed callback with a PDF asset and the file exists on disk', async () => {
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope(RICH_PAYLOAD);

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);

    await waitUntil(() => calls.length >= 1);
    expect(calls).toHaveLength(1);
    const payload = calls[0].payload;
    expect(payload).toMatchObject({ job_id: 'job-mk', status: 'completed', error: null });

    // Media kit uses the single-asset result shape Django reads (result.asset).
    const asset = payload.result!.asset!;
    expect(asset.mime_type).toBe('application/pdf');
    expect(asset.format).toBe('pdf');
    expect(asset.file_size_bytes).toBeGreaterThan(0);
    expect(asset.checksum).toMatch(/^[a-f0-9]{64}$/);

    const onDisk = path.join(root, ...asset.storage_key.split('/'));
    const bytes = await readFile(onDisk);
    expect(bytes.subarray(0, 5).toString('latin1')).toBe(PDF_SIGNATURE);
  });

  it('sends a failed callback when the media-kit payload is invalid', async () => {
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope({});

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);

    await waitUntil(() => calls.length >= 1);
    expect(calls).toHaveLength(1);
    const payload = calls[0].payload;
    expect(payload.status).toBe('failed');
    expect(payload.result).toBeNull();
    expect(payload.error).toMatchObject({
      code: 'render_failed',
      message: 'Falha ao gerar o media kit.',
    });
    expect(payload.error?.details).toMatchObject({ first_error: { code: 'invalid_payload' } });
  });
});
