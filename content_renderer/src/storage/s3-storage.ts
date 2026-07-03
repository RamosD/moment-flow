/**
 * S3-compatible object storage provider (STG-LOCAL-004).
 *
 * Implements {@link StorageProvider} against any S3-compatible endpoint.
 * Validated in this phase against a local MinIO container — see
 * `frontend/docs/01_fundamentos/06_staging_infraestrutura_real_local/`.
 *
 * Deliberately does NOT implement {@link LocalStorageProvider} (no
 * `resolveWithinRoot`/dev `/files` server) — those are filesystem-only
 * concerns. Reports `storage_provider: 's3'` in the Django `Asset` contract,
 * mirroring `Asset.StorageProvider.S3` (`backend_core/apps/core/models.py`) —
 * MinIO is S3-compatible, so no new Django enum value is needed.
 */
import { createHash } from 'node:crypto';

import { PutObjectCommand, S3Client } from '@aws-sdk/client-s3';

import type { AppConfig } from '../config/env';
import type { AssetMetadata } from '../jobs/job.types';
import { StorageFailedError } from '../errors/errors';
import { inferMimeType } from './local-storage';
import type { SaveBufferInput, StorageProvider } from './storage.types';

export type { SaveBufferInput } from './storage.types';

/** Reject path segments that could produce an unsafe or ambiguous object key. */
function assertSafeSegment(value: string, label: string): void {
  if (
    value.length === 0 ||
    value.includes('/') ||
    value.includes('\\') ||
    value.includes('..') ||
    value.includes('\0')
  ) {
    throw new StorageFailedError(`Unsafe ${label} for storage key.`, { [label]: value });
  }
}

export function createS3Storage(config: AppConfig, client?: S3Client): StorageProvider {
  const s3 =
    client ??
    new S3Client({
      endpoint: config.storageEndpoint,
      region: config.storageRegion,
      forcePathStyle: config.storageForcePathStyle,
      credentials: {
        accessKeyId: config.storageAccessKey,
        secretAccessKey: config.storageSecretKey,
      },
    });

  const publicBase = config.storagePublicBaseUrl.replace(/\/+$/, '');

  function buildStorageKey(workspaceId: string, jobId: string, fileName: string): string {
    // Same layout as the local provider — keeps storage_key portable/URL-friendly
    // across providers (storage.types.ts contract).
    return ['workspaces', workspaceId, 'jobs', jobId, fileName].join('/');
  }

  function getPublicUrl(storageKey: string): string {
    return `${publicBase}/${storageKey}`;
  }

  async function saveBuffer(input: SaveBufferInput): Promise<AssetMetadata> {
    assertSafeSegment(input.workspaceId, 'workspaceId');
    assertSafeSegment(input.jobId, 'jobId');
    assertSafeSegment(input.fileName, 'fileName');

    const storageKey = buildStorageKey(input.workspaceId, input.jobId, input.fileName);
    const mimeType = input.mimeType ?? inferMimeType(input.fileName);

    try {
      await s3.send(
        new PutObjectCommand({
          Bucket: config.storageBucket,
          Key: storageKey,
          Body: input.data,
          ContentType: mimeType,
        }),
      );
    } catch (err) {
      // Never include credentials in error details — only operational context.
      throw new StorageFailedError('Failed to upload the rendered file to object storage.', {
        storage_key: storageKey,
        bucket: config.storageBucket,
        cause: err instanceof Error ? err.message : 'unknown',
      });
    }

    const checksum = createHash('sha256').update(input.data).digest('hex');

    return {
      storage_provider: 's3',
      bucket: config.storageBucket,
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

  return { name: 's3', buildStorageKey, saveBuffer };
}
