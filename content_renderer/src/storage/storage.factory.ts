/**
 * Storage provider factory (R-HARD-005, extended by STG-LOCAL-004).
 *
 * Selects the storage implementation from `config.storageProvider`. `local`
 * (filesystem, dev default) and `s3` (S3-compatible, validated against a
 * local MinIO container) are both wired here behind the same
 * {@link StorageProvider} interface. The env loader already rejects unknown
 * provider names at boot — this factory's `default` branch is a defensive guard
 * so a misconfiguration can never silently produce a broken provider.
 */
import type { AppConfig } from '../config/env';
import { ConfigError } from '../errors/errors';
import type { Logger } from '../logging/logger';
import { createLocalStorage } from './local-storage';
import { createS3Storage } from './s3-storage';
import type { StorageProvider } from './storage.types';

export function createStorageProvider(config: AppConfig, logger: Logger): StorageProvider {
  switch (config.storageProvider) {
    case 'local': {
      const provider = createLocalStorage(config);
      // The root is operational, not a secret; the token is never logged.
      logger.info('storage.provider_initialized', { provider: 'local', root: provider.root });
      return provider;
    }
    case 's3': {
      const provider = createS3Storage(config);
      // Endpoint/bucket are operational, not secrets; access/secret key are
      // never logged.
      logger.info('storage.provider_initialized', {
        provider: 's3',
        endpoint: config.storageEndpoint,
        bucket: config.storageBucket,
        force_path_style: config.storageForcePathStyle,
      });
      return provider;
    }
    default: {
      // Unreachable when env validation is in place; kept as a clear hard failure.
      throw new ConfigError(`Unknown STORAGE_PROVIDER "${String(config.storageProvider)}".`, {
        variable: 'STORAGE_PROVIDER',
      });
    }
  }
}
