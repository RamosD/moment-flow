/**
 * Local file server (CR-302).
 *
 * Serves files persisted by the local storage backend under `/files/*`.
 *
 * DEVELOPMENT ONLY. This endpoint exists so rendered assets can be opened
 * locally during development. It is NOT a production file server and is only
 * registered when NODE_ENV !== 'production' (see http/routes.ts). Production
 * serves assets from real object storage (S3/R2) in a later phase.
 *
 * Path traversal is blocked: the requested path is resolved against the storage
 * root and anything escaping it (`../`, absolute paths) yields a 404.
 */
import type { NextFunction, Request, Response } from 'express';

import { NotFoundError } from '../errors/errors';
import type { Logger } from '../logging/logger';
import { inferMimeType } from '../storage/local-storage';
import type { LocalStorageProvider } from '../storage/storage.types';

export function createFileHandler(storage: LocalStorageProvider, fallbackLogger: Logger) {
  return (req: Request, res: Response, next: NextFunction): void => {
    const log: Logger = (res.locals.logger as Logger | undefined) ?? fallbackLogger;

    const raw = (req.params as Record<string, string>)[0] ?? '';
    let relativePath: string;
    try {
      relativePath = decodeURIComponent(raw);
    } catch {
      next(new NotFoundError('File not found.'));
      return;
    }

    const absolutePath = storage.resolveWithinRoot(relativePath);
    if (!absolutePath) {
      log.warn('files.blocked', { reason: 'path_traversal_or_outside_root' });
      next(new NotFoundError('File not found.'));
      return;
    }

    res.type(inferMimeType(absolutePath));
    res.sendFile(absolutePath, (err?: Error) => {
      if (err) {
        // Missing file or any send error → 404 (do not leak filesystem detail).
        next(new NotFoundError('File not found.'));
      }
    });
  };
}
