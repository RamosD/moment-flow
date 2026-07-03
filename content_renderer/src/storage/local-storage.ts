/**
 * Local file storage (CR-301).
 *
 * Persists rendered buffers to disk under a per-workspace / per-job layout and
 * returns Django-compatible asset metadata:
 *
 *   <root>/workspaces/<workspace_id>/jobs/<job_id>/<file_name>
 *
 * IMPORTANT: local storage is for the MVP / development only and is NOT a
 * production backend. The interface is intentionally storage-agnostic so it can
 * later be swapped for S3/R2 without changing the callback/asset contract.
 */
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

import type { AppConfig } from '../config/env';
import type { AssetMetadata } from '../jobs/job.types';
import { StorageFailedError } from '../errors/errors';
import type { LocalStorageProvider, SaveBufferInput } from './storage.types';

// Re-export the centralised storage types from here for backward compatibility.
// `LocalStorage` is kept as an alias of {@link LocalStorageProvider}.
export type { SaveBufferInput } from './storage.types';
export type LocalStorage = LocalStorageProvider;

const MIME_BY_EXTENSION: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.pdf': 'application/pdf',
  '.html': 'text/html',
  '.htm': 'text/html',
  '.json': 'application/json',
  '.txt': 'text/plain',
  '.zip': 'application/zip',
};

/** Best-effort mime type from a file name's extension. */
export function inferMimeType(fileName: string): string {
  const ext = path.extname(fileName).toLowerCase();
  return MIME_BY_EXTENSION[ext] ?? 'application/octet-stream';
}

/** Reject path segments that could escape the per-job directory. */
function assertSafeSegment(value: string, label: string): void {
  if (
    value.length === 0 ||
    value.includes('/') ||
    value.includes('\\') ||
    value.includes('..') ||
    value.includes('\0')
  ) {
    throw new StorageFailedError(`Unsafe ${label} for storage path.`, { [label]: value });
  }
}

export function createLocalStorage(config: AppConfig): LocalStorageProvider {
  const root = path.resolve(config.localStorageRoot);
  const publicBase = config.localStoragePublicBaseUrl.replace(/\/+$/, '');

  function buildStorageKey(workspaceId: string, jobId: string, fileName: string): string {
    // Forward slashes keep keys portable across OSes and URL-friendly.
    return ['workspaces', workspaceId, 'jobs', jobId, fileName].join('/');
  }

  function getPublicUrl(storageKey: string): string {
    return `${publicBase}/${storageKey}`;
  }

  function resolveWithinRoot(relativePath: string): string | null {
    const abs = path.resolve(root, relativePath);
    const rootWithSep = root.endsWith(path.sep) ? root : root + path.sep;
    if (abs === root || abs.startsWith(rootWithSep)) {
      return abs;
    }
    return null;
  }

  async function saveBuffer(input: SaveBufferInput): Promise<AssetMetadata> {
    assertSafeSegment(input.workspaceId, 'workspaceId');
    assertSafeSegment(input.jobId, 'jobId');
    assertSafeSegment(input.fileName, 'fileName');

    const storageKey = buildStorageKey(input.workspaceId, input.jobId, input.fileName);
    const absolutePath = resolveWithinRoot(storageKey);
    if (!absolutePath) {
      // Should be unreachable given assertSafeSegment, but never write outside root.
      throw new StorageFailedError('Resolved storage path escapes the storage root.', {
        storage_key: storageKey,
      });
    }

    try {
      await mkdir(path.dirname(absolutePath), { recursive: true });
      await writeFile(absolutePath, input.data);
    } catch (err) {
      throw new StorageFailedError('Failed to write file to local storage.', {
        storage_key: storageKey,
        cause: err instanceof Error ? err.message : 'unknown',
      });
    }

    const checksum = createHash('sha256').update(input.data).digest('hex');
    const mimeType = input.mimeType ?? inferMimeType(input.fileName);

    return {
      storage_provider: 'local',
      bucket: '',
      storage_key: storageKey,
      file_name: input.fileName,
      mime_type: mimeType,
      file_size_bytes: input.data.length,
      width: input.width ?? null,
      height: input.height ?? null,
      duration_seconds: input.durationSeconds ?? null,
      checksum,
      public_url: getPublicUrl(storageKey),
    };
  }

  return { name: 'local', root, buildStorageKey, saveBuffer, resolveWithinRoot, getPublicUrl };
}
