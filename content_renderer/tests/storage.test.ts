import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { loadConfig, type AppConfig } from '../src/config/env';
import { ConfigError, StorageFailedError } from '../src/errors/errors';
import { createLogger } from '../src/logging/logger';
import { createLocalStorage } from '../src/storage/local-storage';
import { createStorageProvider } from '../src/storage/storage.factory';
import { isLocalStorageProvider } from '../src/storage/storage.types';

const silentLogger = createLogger({ write: () => {} });

function configFor(root: string, overrides: NodeJS.ProcessEnv = {}) {
  return loadConfig({
    NODE_ENV: 'test',
    INTERNAL_API_TOKEN: 't',
    LOCAL_STORAGE_ROOT: root,
    LOCAL_STORAGE_PUBLIC_BASE_URL: 'http://localhost:8002/files',
    ...overrides,
  });
}

/** Keys of the Django `Asset` contract — must stay stable (R-HARD-005). */
const ASSET_KEYS = [
  'storage_provider',
  'bucket',
  'storage_key',
  'file_name',
  'mime_type',
  'file_size_bytes',
  'width',
  'height',
  'duration_seconds',
  'checksum',
  'public_url',
].sort();

describe('local storage', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-storage-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('saves a buffer under workspaces/<ws>/jobs/<job>/<file> with Django-compatible metadata', async () => {
    const storage = createLocalStorage(configFor(root));
    const data = Buffer.from('hello-png-bytes');

    const meta = await storage.saveBuffer({
      workspaceId: 'ws-1',
      jobId: 'job-1',
      fileName: 'output_001.png',
      data,
    });

    expect(meta).toMatchObject({
      storage_provider: 'local',
      bucket: '',
      storage_key: 'workspaces/ws-1/jobs/job-1/output_001.png',
      file_name: 'output_001.png',
      mime_type: 'image/png',
      file_size_bytes: data.length,
      width: null,
      height: null,
      duration_seconds: null,
    });

    const written = await readFile(
      path.join(root, 'workspaces', 'ws-1', 'jobs', 'job-1', 'output_001.png'),
    );
    expect(written.equals(data)).toBe(true);
  });

  it('computes a sha256 checksum and a public_url', async () => {
    const storage = createLocalStorage(configFor(root));
    const data = Buffer.from('checksum-content');

    const meta = await storage.saveBuffer({
      workspaceId: 'ws',
      jobId: 'job',
      fileName: 'report.pdf',
      data,
    });

    expect(meta.mime_type).toBe('application/pdf');
    expect(meta.checksum).toBe(createHash('sha256').update(data).digest('hex'));
    expect(meta.public_url).toBe('http://localhost:8002/files/workspaces/ws/jobs/job/report.pdf');
  });

  it('honours an explicit mime type and width/height', async () => {
    const storage = createLocalStorage(configFor(root));

    const meta = await storage.saveBuffer({
      workspaceId: 'ws',
      jobId: 'job',
      fileName: 'card',
      data: Buffer.from('x'),
      mimeType: 'image/webp',
      width: 1080,
      height: 1080,
    });

    expect(meta.mime_type).toBe('image/webp');
    expect(meta.width).toBe(1080);
    expect(meta.height).toBe(1080);
  });

  it('rejects a fileName that attempts path traversal', async () => {
    const storage = createLocalStorage(configFor(root));

    await expect(
      storage.saveBuffer({
        workspaceId: 'ws',
        jobId: 'job',
        fileName: '../escape.png',
        data: Buffer.from('x'),
      }),
    ).rejects.toBeInstanceOf(StorageFailedError);
  });

  it('resolveWithinRoot blocks traversal and absolute paths', () => {
    const storage = createLocalStorage(configFor(root));

    expect(storage.resolveWithinRoot('workspaces/ws/jobs/job/a.png')).not.toBeNull();
    expect(storage.resolveWithinRoot('../../etc/passwd')).toBeNull();
    expect(storage.resolveWithinRoot('..')).toBeNull();
    expect(storage.resolveWithinRoot(path.resolve(root, '..', 'outside.txt'))).toBeNull();
  });
});

describe('storage provider abstraction (R-HARD-005)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-storage-prov-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it('LocalStorage implements the StorageProvider interface', () => {
    const storage = createLocalStorage(configFor(root));

    expect(storage.name).toBe('local');
    expect(typeof storage.buildStorageKey).toBe('function');
    expect(typeof storage.saveBuffer).toBe('function');
    expect(typeof storage.resolveWithinRoot).toBe('function');
    expect(typeof storage.getPublicUrl).toBe('function');
    expect(isLocalStorageProvider(storage)).toBe(true);
    expect(storage.getPublicUrl('workspaces/ws/jobs/job/a.png')).toBe(
      'http://localhost:8002/files/workspaces/ws/jobs/job/a.png',
    );
  });

  it('createStorageProvider(local) returns a working local provider', async () => {
    const provider = createStorageProvider(configFor(root), silentLogger);

    expect(provider.name).toBe('local');
    expect(isLocalStorageProvider(provider)).toBe(true);

    // The provider really persists a buffer (renderers keep working).
    const meta = await provider.saveBuffer({
      workspaceId: 'ws',
      jobId: 'job',
      fileName: 'output_001.png',
      data: Buffer.from('PNG'),
    });
    expect(meta.storage_provider).toBe('local');
    const written = await readFile(path.join(root, 'workspaces', 'ws', 'jobs', 'job', 'output_001.png'));
    expect(written.toString()).toBe('PNG');
  });

  it('STORAGE_PROVIDER=local is accepted by the env loader', () => {
    const config = configFor(root, { STORAGE_PROVIDER: 'local' });
    expect(config.storageProvider).toBe('local');
  });

  it('an unknown STORAGE_PROVIDER fails fast at boot', () => {
    expect(() => configFor(root, { STORAGE_PROVIDER: 's3' })).toThrow(ConfigError);
  });

  it('the factory rejects an unknown provider with a clear error', () => {
    // Force an invalid provider past the env validation to exercise the factory guard.
    const broken = { ...configFor(root), storageProvider: 'r2' as unknown } as AppConfig;
    expect(() => createStorageProvider(broken, silentLogger)).toThrow(ConfigError);
  });

  it('keeps the Django Asset contract unchanged', async () => {
    const provider = createStorageProvider(configFor(root), silentLogger);
    const meta = await provider.saveBuffer({
      workspaceId: 'ws',
      jobId: 'job',
      fileName: 'report.pdf',
      data: Buffer.from('%PDF-'),
    });

    expect(Object.keys(meta).sort()).toEqual(ASSET_KEYS);
    expect(meta).toMatchObject({ storage_provider: 'local', bucket: '' });
  });
});
