/**
 * Storage abstraction types (R-HARD-005, extended by STG-LOCAL-004).
 *
 * Centralises the storage contract so renderers depend on an interface
 * ({@link StorageProvider}) rather than a concrete backend. `local`
 * (filesystem, dev default) and `s3` (S3-compatible, validated against a
 * local MinIO container) are both implemented behind this same interface
 * WITHOUT touching renderers or changing the Django `Asset` contract.
 *
 * The `Asset` metadata shape is owned by `jobs/job.types` (it is part of the
 * Django callback contract) and re-exported here so storage consumers have a
 * single import point.
 */
import type { AssetMetadata } from '../jobs/job.types';

export type { AssetMetadata };

/**
 * Storage backends known to the renderer.
 *
 * `r2`/`gcs` are intentionally NOT listed yet — adding them here (plus a
 * provider implementation and the env validation) would be a future
 * migration step. Keeping the union narrow means an unknown
 * `STORAGE_PROVIDER` fails fast at boot.
 */
export type StorageProviderName = 'local' | 's3';

/** Input for persisting a rendered buffer. */
export interface SaveBufferInput {
  workspaceId: string;
  jobId: string;
  fileName: string;
  data: Buffer;
  /** Explicit mime type; inferred from the file extension when omitted. */
  mimeType?: string;
  width?: number | null;
  height?: number | null;
  durationSeconds?: number | null;
}

/**
 * Storage abstraction the renderers depend on. Deliberately minimal — just what
 * is needed to persist a buffer and return Django-compatible asset metadata —
 * so it is satisfiable by object storage (S3/R2) without filesystem semantics.
 */
export interface StorageProvider {
  /** Provider identifier (mirrors `AssetMetadata.storage_provider`). */
  readonly name: StorageProviderName;
  /** Build the stable, URL-friendly storage key for a workspace/job/file. */
  buildStorageKey(workspaceId: string, jobId: string, fileName: string): string;
  /** Persist a buffer and return Django-compatible asset metadata. */
  saveBuffer(input: SaveBufferInput): Promise<AssetMetadata>;
}

/**
 * Filesystem-backed provider. Adds the dev-only capabilities the local
 * `GET /files/*` server needs (resolving a request path safely within the root)
 * and a public-URL helper. An object-storage provider would NOT implement these.
 */
export interface LocalStorageProvider extends StorageProvider {
  readonly name: 'local';
  /** Absolute root directory where files are stored. */
  readonly root: string;
  /**
   * Resolve a relative path (e.g. the part after `/files/`) to an absolute path
   * guaranteed to live inside `root`. Returns `null` for traversal attempts or
   * paths that escape the root (defence against `../`, absolute paths, etc.).
   */
  resolveWithinRoot(relativePath: string): string | null;
  /** Public URL where a stored file can be fetched (dev `/files` server). */
  getPublicUrl(storageKey: string): string;
}

/** Narrow a {@link StorageProvider} to a {@link LocalStorageProvider}. */
export function isLocalStorageProvider(
  provider: StorageProvider,
): provider is LocalStorageProvider {
  return (
    provider.name === 'local' &&
    typeof (provider as LocalStorageProvider).resolveWithinRoot === 'function'
  );
}
