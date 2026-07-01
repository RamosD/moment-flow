/**
 * HTTP middleware: request-context logging, internal authentication, job header
 * consistency, and centralised error handling.
 */
import { createHash, randomUUID, timingSafeEqual } from 'node:crypto';

import type { NextFunction, Request, Response } from 'express';

import type { AppConfig } from '../config/env';
import type { Logger } from '../logging/logger';
import type { JobEnvelope } from '../jobs/job.types';
import { AppError, BadRequestError, NotFoundError, UnauthorizedError, toAppError } from '../errors/errors';

/**
 * Attaches a correlation id and a request-scoped child logger to `res.locals`,
 * and logs request completion. The incoming `X-Request-ID` is honoured when
 * present so logs correlate across services.
 */
export function requestContext(logger: Logger) {
  return (req: Request, res: Response, next: NextFunction): void => {
    const requestId = (req.header('x-request-id') || randomUUID()).toString();
    const reqLogger = logger.child({ request_id: requestId });

    res.locals.requestId = requestId;
    res.locals.logger = reqLogger;
    res.setHeader('x-request-id', requestId);

    res.on('finish', () => {
      reqLogger.info('http.request', {
        method: req.method,
        path: req.path,
        status: res.statusCode,
      });
    });

    next();
  };
}

/** Constant-time string equality, length-safe via fixed-size SHA-256 digests. */
function secureEquals(a: string, b: string): boolean {
  const da = createHash('sha256').update(a).digest();
  const db = createHash('sha256').update(b).digest();
  return timingSafeEqual(da, db);
}

/**
 * Internal authentication middleware (CR-101).
 *
 * Validates `X-Internal-Token` against the configured token using a
 * constant-time comparison. The token value is NEVER logged or echoed.
 *
 * When the configured token is empty the service is in explicit insecure local
 * mode (development with ALLOW_INSECURE_EMPTY_TOKEN=true, or tests); auth is
 * bypassed and a warning is logged. An empty token cannot occur in production —
 * the env loader refuses to boot.
 */
export function internalAuth(config: AppConfig, fallbackLogger: Logger) {
  return (req: Request, res: Response, next: NextFunction): void => {
    const log: Logger = (res.locals.logger as Logger | undefined) ?? fallbackLogger;

    if (config.insecureTokenMode) {
      log.warn('auth.bypassed_insecure_mode', { path: req.path });
      next();
      return;
    }

    const provided = req.header('x-internal-token') ?? '';
    if (provided === '' || !secureEquals(provided, config.internalApiToken)) {
      log.warn('auth.rejected', {
        path: req.path,
        reason: provided === '' ? 'missing_token' : 'invalid_token',
      });
      next(new UnauthorizedError());
      return;
    }

    next();
  };
}

/**
 * Validate that the job headers are consistent with the validated envelope
 * (CR-102). `X-Workspace-ID` and `X-Job-ID` mismatches (or absence) are hard
 * failures (400). A `X-Request-ID` mismatch is a documented controlled warning —
 * the body value is treated as authoritative — so it does not reject the job.
 */
export function enforceJobHeaderConsistency(
  req: Request,
  envelope: JobEnvelope,
  logger: Logger,
): void {
  const headerWorkspace = req.header('x-workspace-id');
  const headerJob = req.header('x-job-id');
  const headerRequest = req.header('x-request-id');

  if (!headerWorkspace || headerWorkspace !== envelope.workspace_id) {
    throw new BadRequestError('X-Workspace-ID header does not match body.workspace_id.', {
      header: 'X-Workspace-ID',
    });
  }
  if (!headerJob || headerJob !== envelope.job_id) {
    throw new BadRequestError('X-Job-ID header does not match body.job_id.', {
      header: 'X-Job-ID',
    });
  }
  if (headerRequest && headerRequest !== envelope.request_id) {
    logger.warn('job.request_id_mismatch', {
      header_request_id: headerRequest,
      body_request_id: envelope.request_id,
    });
  }
}

/** 404 handler for unmatched routes. */
export function notFoundHandler(req: Request, _res: Response, next: NextFunction): void {
  next(new NotFoundError(`Route not found: ${req.method} ${req.path}`));
}

/**
 * Centralised error handler. Converts any thrown value into the normalised
 * error envelope and never leaks secrets (the logger redacts sensitive keys).
 */
export function errorHandler(fallbackLogger: Logger) {
  // Express identifies error handlers by their 4-arg signature; `next` must stay.
  return (err: unknown, _req: Request, res: Response, _next: NextFunction): void => {
    const appError: AppError = toAppError(err);
    const log: Logger = (res.locals.logger as Logger | undefined) ?? fallbackLogger;

    const logFields = {
      code: appError.code,
      status: appError.statusCode,
      details: appError.details,
    };
    if (appError.statusCode >= 500) {
      log.error('http.error', logFields);
    } else {
      log.warn('http.error', logFields);
    }

    if (res.headersSent) {
      return;
    }
    res.status(appError.statusCode).json({ error: appError.toJSON() });
  };
}
