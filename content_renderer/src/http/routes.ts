/**
 * Route registration.
 *
 * Exposes:
 *  - `GET /health`  — public liveness probe.
 *  - `POST /jobs`   — internal, token-protected job intake.
 *  - `GET /files/*` — DEV ONLY local file server (not registered in production).
 */
import { Router, type NextFunction, type Request, type Response } from 'express';

import { RENDERER_NAME, RENDERER_VERSION } from '../constants';
import type { AppConfig } from '../config/env';
import type { JobController } from '../jobs/job.controller';
import type { Logger } from '../logging/logger';
import { isLocalStorageProvider, type StorageProvider } from '../storage/storage.types';
import { createFileHandler } from './files';
import { internalAuth } from './middleware';

export interface RouteDeps {
  config: AppConfig;
  logger: Logger;
  jobController: JobController;
  storage: StorageProvider;
}

export function buildRouter(deps: RouteDeps): Router {
  const { config, logger, jobController, storage } = deps;
  const router = Router();

  // GET /health — liveness probe (CR-001). Public, no auth.
  router.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({
      status: 'ok',
      service: RENDERER_NAME,
      version: RENDERER_VERSION,
      uptime_seconds: Math.round(process.uptime()),
      timestamp: new Date().toISOString(),
    });
  });

  // POST /jobs — internal job intake (CR-201). Auth runs first (403 on failure).
  router.post(
    '/jobs',
    internalAuth(config, logger),
    (req: Request, res: Response, next: NextFunction) => {
      jobController.receiveJob(req, res).catch(next);
    },
  );

  // GET /files/* — DEV ONLY (CR-302). Serves locally stored assets. Only
  // registered for the local provider and outside production; object-storage
  // providers (S3/R2) serve their own URLs and have no within-root resolver.
  if (config.nodeEnv !== 'production' && isLocalStorageProvider(storage)) {
    router.get(/^\/files\/(.+)/, createFileHandler(storage, logger));
  }

  return router;
}
