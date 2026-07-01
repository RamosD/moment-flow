/**
 * Express application factory.
 *
 * `createApp` is pure — it builds and returns the configured app without
 * binding a port — so it can be exercised directly by tests (e.g. supertest).
 * Port binding and process lifecycle live in `server.ts`.
 */
import express, { type Express } from 'express';

import { createCallbackClient, type CallbackClient } from './callbacks/callback.client';
import type { AppConfig } from './config/env';
import { buildRouter } from './http/routes';
import { errorHandler, notFoundHandler, requestContext } from './http/middleware';
import { createJobController } from './jobs/job.controller';
import { createJobService } from './jobs/job.service';
import { logger as defaultLogger, type Logger } from './logging/logger';
import { createStorageProvider } from './storage/storage.factory';
import type { StorageProvider } from './storage/storage.types';

export interface CreateAppOptions {
  logger?: Logger;
  /** Override the storage backend (tests use a temp root). */
  storage?: StorageProvider;
  /** Override the callback client (tests inject a recording mock — no real HTTP). */
  callbackClient?: CallbackClient;
}

export function createApp(config: AppConfig, options: CreateAppOptions = {}): Express {
  const log = options.logger ?? defaultLogger;

  // Compose the dependency graph (storage + callback → service → controller).
  const storage = options.storage ?? createStorageProvider(config, log);
  const callbackClient = options.callbackClient ?? createCallbackClient({ config, logger: log });
  const jobService = createJobService({ config, logger: log, storage, callbackClient });
  const jobController = createJobController({ jobService, logger: log });

  const app = express();
  app.disable('x-powered-by');

  // Cap the accepted body size at the configured payload limit.
  app.use(express.json({ limit: config.maxJobPayloadBytes }));

  app.use(requestContext(log));
  app.use(buildRouter({ config, logger: log, jobController, storage }));

  // 404 + centralised error handling must be registered last.
  app.use(notFoundHandler);
  app.use(errorHandler(log));

  return app;
}
