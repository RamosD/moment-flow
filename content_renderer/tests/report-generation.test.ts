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
import { renderReportGeneration } from '../src/renderers/reports';
import { renderReportHtml } from '../src/renderers/reports/report.html';
import { buildReportModel, parseReportPayload } from '../src/renderers/reports/report.model';
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

const SAMPLE_PAYLOAD = {
  report_type: 'weekly_growth',
  title: 'Weekly Growth Report',
  period_start: '2026-06-01',
  period_end: '2026-06-07',
  campaign: { name: 'Summer Push' },
  artist: { name: 'Nova' },
  track: { title: 'Midnight Drive' },
  sections: [
    { heading: 'Highlights', body: 'Strong week across platforms.', items: ['+12% streams', 'New playlist add'] },
    'A plain-string section.',
  ],
  outputs: [{ id: 'out-1' }, { id: 'out-2' }],
  smart_link_stats: { total_clicks: 1234, unique_visitors: 980, conversions: 87 },
  branding: { brand_color: '#0984E3' },
};

function makeEnvelope(
  payload: Record<string, unknown>,
  overrides: Partial<JobEnvelope> = {},
): JobEnvelope {
  return {
    job_id: 'job-rep',
    workspace_id: 'ws-rep',
    request_id: 'req-rep',
    job_type: 'report_generation',
    callback_url: 'http://callback.test/cb',
    entity: { type: 'report', id: 'rep-1' },
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

describe('report model + html', () => {
  it('rejects a payload with no title, report_type or sections', () => {
    expect(parseReportPayload({}).success).toBe(false);
    expect(parseReportPayload({ campaign: { name: 'x' } }).success).toBe(false);
    // A wrong-typed field is also invalid.
    expect(parseReportPayload({ title: 'ok', sections: 'not-an-array' }).success).toBe(false);
  });

  it('accepts a valid payload and normalises it into a model', () => {
    const parsed = parseReportPayload(SAMPLE_PAYLOAD);
    expect(parsed.success).toBe(true);
    if (!parsed.success) return;

    const model = buildReportModel(parsed.data);
    expect(model.reportType).toBe('weekly_growth');
    expect(model.title).toBe('Weekly Growth Report');
    expect(model.periodLabel).toBe('2026-06-01 — 2026-06-07');
    expect(model.artistName).toBe('Nova');
    expect(model.campaignName).toBe('Summer Push');
    expect(model.trackTitle).toBe('Midnight Drive');
    expect(model.sections).toHaveLength(2);
    expect(model.stats.map((s) => s.label)).toContain('Total Clicks');
    expect(model.relatedOutputCount).toBe(2);
    expect(model.brandColor).toBe('#0984E3');
  });

  it('renders an HTML document containing the report data (escaped)', () => {
    const parsed = parseReportPayload(SAMPLE_PAYLOAD);
    if (!parsed.success) throw new Error('expected valid payload');
    const html = renderReportHtml(buildReportModel(parsed.data));

    expect(html).toContain('<!DOCTYPE html>');
    for (const text of [
      'Weekly Growth Report',
      '2026-06-01 — 2026-06-07',
      'Nova',
      'Summer Push',
      'Midnight Drive',
      'Highlights',
      'Total Clicks',
      'Generated at',
    ]) {
      expect(html).toContain(text);
    }
  });

  it('escapes a malicious title so no raw markup is injected', () => {
    const parsed = parseReportPayload({
      report_type: 'weekly',
      title: '<script>alert(1)</script>',
    });
    if (!parsed.success) throw new Error('expected valid payload');
    const html = renderReportHtml(buildReportModel(parsed.data));
    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
  });
});

describe('report_generation renderer — unit', () => {
  let root: string;
  let storage: LocalStorage;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-report-'));
    storage = createLocalStorage(configFor(root));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('generates a real PDF by default and persists it to local storage', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderReportGeneration(makeEnvelope(SAMPLE_PAYLOAD), context);

    expect(result.status).toBe('completed');
    const output = result.outputs[0];
    expect(output.output_type).toBe('report');
    expect(output.format).toBe('pdf');
    expect(output.metadata?.fallback_html).toBe(false);

    const asset = output.asset!;
    expect(asset.mime_type).toBe('application/pdf');

    // The file really exists on disk and begins with the PDF signature.
    const onDisk = path.join(root, ...asset.storage_key.split('/'));
    const bytes = await readFile(onDisk);
    expect(bytes.length).toBeGreaterThan(0);
    expect(bytes.subarray(0, 5).toString('latin1')).toBe(PDF_SIGNATURE);
  });

  it('produces Django-compatible asset metadata', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderReportGeneration(makeEnvelope(SAMPLE_PAYLOAD), context);
    const asset = result.outputs[0].asset!;

    expect(asset).toMatchObject({
      storage_provider: 'local',
      bucket: '',
      file_name: 'report.pdf',
      mime_type: 'application/pdf',
      width: null,
      height: null,
      duration_seconds: null,
    });
    expect(asset.storage_key).toBe('workspaces/ws-rep/jobs/job-rep/report.pdf');
    expect(asset.file_size_bytes).toBeGreaterThan(0);
    expect(asset.checksum).toMatch(/^[a-f0-9]{64}$/);
  });

  it('falls back to HTML when REPORT_OUTPUT_FORMAT=html', async () => {
    const config = configFor(root, { REPORT_OUTPUT_FORMAT: 'html' });
    const context: RenderContext = { config, logger: silentLogger, storage };
    const result = await renderReportGeneration(makeEnvelope(SAMPLE_PAYLOAD), context);

    expect(result.status).toBe('completed');
    const output = result.outputs[0];
    expect(output.format).toBe('html');
    expect(output.metadata?.fallback_html).toBe(true);
    expect(output.asset?.mime_type).toBe('text/html');
    expect(output.asset?.file_name).toBe('report.html');

    const onDisk = path.join(root, ...output.asset!.storage_key.split('/'));
    const html = await readFile(onDisk, 'utf8');
    expect(html).toContain('Weekly Growth Report');
  });

  it('returns a failed result for an invalid payload', async () => {
    const context: RenderContext = { config: configFor(root), logger: silentLogger, storage };
    const result = await renderReportGeneration(makeEnvelope({}), context);

    expect(result.status).toBe('failed');
    expect(result.outputs[0].status).toBe('failed');
    expect(result.outputs[0].metadata?.error).toMatchObject({ code: 'invalid_payload' });
  });

  it('returns a failed result when storage fails', async () => {
    const context: RenderContext = {
      config: configFor(root),
      logger: silentLogger,
      storage: failingStorage(storage),
    };
    const result = await renderReportGeneration(makeEnvelope(SAMPLE_PAYLOAD), context);

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

describe('POST /jobs report_generation — integration (mocked callback)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-report-e2e-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('sends a completed callback with a PDF asset and the file exists on disk', async () => {
    const { client, calls } = recordingCallback();
    const app = createApp(configFor(root), { logger: silentLogger, callbackClient: client });
    const body = makeEnvelope(SAMPLE_PAYLOAD);

    const res = await request(app).post('/jobs').set(authHeaders(body)).send(body);

    expect(res.status).toBe(202);

    await waitUntil(() => calls.length >= 1);
    expect(calls).toHaveLength(1);
    const payload = calls[0].payload;
    expect(payload).toMatchObject({ job_id: 'job-rep', status: 'completed', error: null });

    // Report uses the single-asset result shape Django reads (result.asset).
    const asset = payload.result!.asset!;
    expect(asset.mime_type).toBe('application/pdf');
    expect(asset.format).toBe('pdf');
    expect(asset.file_size_bytes).toBeGreaterThan(0);
    expect(asset.checksum).toMatch(/^[a-f0-9]{64}$/);

    const onDisk = path.join(root, ...asset.storage_key.split('/'));
    const bytes = await readFile(onDisk);
    expect(bytes.subarray(0, 5).toString('latin1')).toBe(PDF_SIGNATURE);
  });

  it('sends a failed callback when the report payload is invalid', async () => {
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
      message: 'Falha ao gerar o relatório.',
    });
    expect(payload.error?.details).toMatchObject({
      first_error: { code: 'invalid_payload' },
    });
  });
});
