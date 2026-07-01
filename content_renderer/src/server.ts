/**
 * Service entrypoint: load and validate configuration, build the app, bind the
 * HTTP port, and wire graceful shutdown.
 */
import { createApp } from './app';
import { loadConfig } from './config/env';
import { RENDERER_NAME, RENDERER_VERSION } from './constants';
import { AppError } from './errors/errors';
import { logger } from './logging/logger';

function start(): void {
  let config;
  try {
    config = loadConfig();
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown configuration error.';
    const details = err instanceof AppError ? err.details : {};
    logger.error('config.invalid', { message, details });
    process.exit(1);
    return;
  }

  const app = createApp(config, { logger });

  const server = app.listen(config.port, () => {
    logger.info('server.started', {
      service: RENDERER_NAME,
      version: RENDERER_VERSION,
      port: config.port,
      node_env: config.nodeEnv,
      insecure_mode: config.insecureTokenMode,
    });
    if (config.insecureTokenMode) {
      logger.warn('server.insecure_token_mode', {
        message:
          'INTERNAL_API_TOKEN is empty — internal authentication is disabled (local insecure mode).',
      });
    }
  });

  const shutdown = (signal: string): void => {
    logger.info('server.shutdown', { signal });
    server.close(() => process.exit(0));
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

start();
