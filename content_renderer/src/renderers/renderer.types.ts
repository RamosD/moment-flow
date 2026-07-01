/**
 * Shared types for renderers.
 *
 * Each renderer takes a validated {@link JobEnvelope} plus a {@link RenderContext}
 * (configuration, a job-scoped logger and the storage backend) and returns a
 * {@link RenderResult}.
 */
import type { AppConfig } from '../config/env';
import type { Logger } from '../logging/logger';
import type { StorageProvider } from '../storage/storage.types';
import type { JobEnvelope, RenderResult } from '../jobs/job.types';

export interface RenderContext {
  config: AppConfig;
  logger: Logger;
  /**
   * Storage backend used to persist rendered buffers and return asset metadata.
   * Depends on the {@link StorageProvider} abstraction (R-HARD-005), not on a
   * concrete backend, so the local provider can be swapped for S3/R2 later.
   */
  storage: StorageProvider;
}

export type Renderer = (envelope: JobEnvelope, context: RenderContext) => Promise<RenderResult>;
