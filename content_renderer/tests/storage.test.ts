import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { PutObjectCommand, type S3Client } from '@aws-sdk/client-s3';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { loadConfig, type AppConfig } from '../src/config/env';
import { ConfigError, StorageFailedError } from '../src/errors/errors';
import { createLogger } from '../src/logging/logger';
import { createLocalStorage } from '../src/storage/local-storage';
import { createS3Storage } from '../src/storage/s3-storage';
import { createStorageProvider } from '../src/storage/storage.factory';
import { isLocalStorageProvider } from '../src/storage/storage.types';

const silentLogger = createLogger({ write: () => {} });

function configFor(root: string, overrides: NodeJS.ProcessEnv = {}) {
  return loadConfig({
    NODE_ENV: 'test',
    INTERNAL_API_TOKEN: 't',
    LOCAL_STORAGE_ROOT: root,
    LOCAL_STORAGE_PUBLIC_BASE_URL: 'http://localhost:8202/files',
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
    expect(meta.public_url).toBe('http://localhost:8202/files/workspaces/ws/jobs/job/report.pdf');
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
      'http://localhost:8202/files/workspaces/ws/jobs/job/a.png',
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
    expect(() => configFor(root, { STORAGE_PROVIDER: 'r2' })).toThrow(ConfigError);
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

  it('createStorageProvider(s3) returns a provider without making a network call', () => {
    // S3Client construction is lazy (no connection until .send()), so this is
    // a pure unit assertion — no MinIO/network dependency.
    const config = configFor(root, {
      STORAGE_PROVIDER: 's3',
      STORAGE_ENDPOINT: 'http://127.0.0.1:9000',
      STORAGE_BUCKET: 'chartrex-staging',
      STORAGE_ACCESS_KEY: 'minio-access-key',
      STORAGE_SECRET_KEY: 'minio-secret-key',
    });
    const provider = createStorageProvider(config, silentLogger);
    expect(provider.name).toBe('s3');
    expect(isLocalStorageProvider(provider)).toBe(false);
  });
});

describe('S3-compatible storage provider (STG-LOCAL-004)', () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'cr-storage-s3-'));
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  function s3ConfigFor(overrides: NodeJS.ProcessEnv = {}) {
    return configFor(root, {
      STORAGE_PROVIDER: 's3',
      STORAGE_ENDPOINT: 'http://127.0.0.1:9000',
      STORAGE_BUCKET: 'chartrex-staging',
      STORAGE_ACCESS_KEY: 'minio-access-key',
      STORAGE_SECRET_KEY: 'minio-secret-key',
      ...overrides,
    });
  }

  /** Fake S3Client — records the last command sent, never touches the network. */
  function fakeClient() {
    const send = vi.fn().mockResolvedValue({});
    return { send: send as unknown as S3Client['send'] } as unknown as S3Client;
  }

  it('uploads via PutObjectCommand and returns Django-compatible metadata', async () => {
    const client = fakeClient();
    const storage = createS3Storage(s3ConfigFor(), client);
    const data = Buffer.from('hello-png-bytes');

    const meta = await storage.saveBuffer({
      workspaceId: 'ws-1',
      jobId: 'job-1',
      fileName: 'output_001.png',
      data,
    });

    expect(client.send).toHaveBeenCalledTimes(1);
    const command = (client.send as ReturnType<typeof vi.fn>).mock.calls[0][0] as PutObjectCommand;
    expect(command).toBeInstanceOf(PutObjectCommand);
    expect(command.input).toMatchObject({
      Bucket: 'chartrex-staging',
      Key: 'workspaces/ws-1/jobs/job-1/output_001.png',
      ContentType: 'image/png',
    });

    expect(meta).toMatchObject({
      storage_provider: 's3',
      bucket: 'chartrex-staging',
      storage_key: 'workspaces/ws-1/jobs/job-1/output_001.png',
      file_name: 'output_001.png',
      mime_type: 'image/png',
      file_size_bytes: data.length,
      width: null,
      height: null,
      duration_seconds: null,
    });
    expect(meta.public_url).toBe(
      'http://127.0.0.1:9000/chartrex-staging/workspaces/ws-1/jobs/job-1/output_001.png',
    );
  });

  it('computes a sha256 checksum identical to the local provider', async () => {
    const client = fakeClient();
    const storage = createS3Storage(s3ConfigFor(), client);
    const data = Buffer.from('checksum-content');

    const meta = await storage.saveBuffer({
      workspaceId: 'ws',
      jobId: 'job',
      fileName: 'report.pdf',
      data,
    });

    expect(meta.checksum).toBe(createHash('sha256').update(data).digest('hex'));
  });

  it('honours an explicit mime type and width/height', async () => {
    const client = fakeClient();
    const storage = createS3Storage(s3ConfigFor(), client);

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

  it('rejects a fileName that attempts path traversal without calling the client', async () => {
    const client = fakeClient();
    const storage = createS3Storage(s3ConfigFor(), client);

    await expect(
      storage.saveBuffer({
        workspaceId: 'ws',
        jobId: 'job',
        fileName: '../escape.png',
        data: Buffer.from('x'),
      }),
    ).rejects.toBeInstanceOf(StorageFailedError);
    expect(client.send).not.toHaveBeenCalled();
  });

  it('wraps a failed upload in StorageFailedError without leaking credentials', async () => {
    const client = {
      send: vi.fn().mockRejectedValue(new Error('connection refused')),
    } as unknown as S3Client;
    const storage = createS3Storage(s3ConfigFor(), client);

    const error = await storage
      .saveBuffer({ workspaceId: 'ws', jobId: 'job', fileName: 'x.png', data: Buffer.from('x') })
      .catch((err: unknown) => err);

    expect(error).toBeInstanceOf(StorageFailedError);
    const serialised = JSON.stringify((error as StorageFailedError).toJSON());
    expect(serialised).not.toContain('minio-secret-key');
    expect(serialised).not.toContain('minio-access-key');
  });

  it('keeps the Django Asset contract unchanged', async () => {
    const client = fakeClient();
    const storage = createS3Storage(s3ConfigFor(), client);

    const meta = await storage.saveBuffer({
      workspaceId: 'ws',
      jobId: 'job',
      fileName: 'report.pdf',
      data: Buffer.from('%PDF-'),
    });

    expect(Object.keys(meta).sort()).toEqual(ASSET_KEYS);
  });
});
