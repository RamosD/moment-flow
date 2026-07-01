import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';

import { createApp } from '../src/app';
import { loadConfig } from '../src/config/env';
import { createLogger } from '../src/logging/logger';
import { createLocalStorage } from '../src/storage/local-storage';

describe('GET /files/* (development only)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-files-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  function buildApp(nodeEnv: 'test' | 'production' = 'test') {
    const config = loadConfig({
      NODE_ENV: nodeEnv,
      INTERNAL_API_TOKEN: 't',
      LOCAL_STORAGE_ROOT: root,
    });
    return createApp(config, { logger: createLogger({ write: () => {} }) });
  }

  async function seedFile(fileName = 'a.png', data = Buffer.from('PNGDATA')) {
    const storage = createLocalStorage(
      loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: 't', LOCAL_STORAGE_ROOT: root }),
    );
    return storage.saveBuffer({ workspaceId: 'ws', jobId: 'job', fileName, data });
  }

  it('serves a stored file', async () => {
    const data = Buffer.from('PNGDATA');
    const meta = await seedFile('a.png', data);

    const res = await request(buildApp()).get(`/files/${meta.storage_key}`);

    expect(res.status).toBe(200);
    expect(res.headers['content-type']).toContain('image/png');
    expect(res.headers['content-length']).toBe(String(data.length));
  });

  it('returns 404 for a path traversal attempt', async () => {
    await seedFile();

    const res = await request(buildApp()).get('/files/..%2f..%2f..%2fsecret.txt');

    expect(res.status).toBe(404);
  });

  it('returns 404 for a missing file', async () => {
    const res = await request(buildApp()).get('/files/workspaces/ws/jobs/job/missing.png');

    expect(res.status).toBe(404);
  });

  it('is not registered in production', async () => {
    await seedFile();

    const res = await request(buildApp('production')).get('/files/workspaces/ws/jobs/job/a.png');

    expect(res.status).toBe(404);
  });
});
