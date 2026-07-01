/**
 * Normalised error model for the renderer.
 *
 * Every operational failure is expressed as an {@link AppError} carrying a
 * stable machine-readable `code`, an HTTP `statusCode`, and a safe `details`
 * object. The error codes mirror the contract expected by the Backend Core
 * (Django) callback (see backlog CR-801) so failures can be reported verbatim.
 *
 * `details` must never contain secrets (tokens, credentials). The structured
 * logger redacts sensitive keys as a defence-in-depth measure, but callers
 * should not place secrets here in the first place.
 */

export type ErrorCode =
  | 'invalid_payload'
  | 'unsupported_job_type'
  | 'unsupported_template'
  | 'render_failed'
  | 'storage_failed'
  | 'callback_failed'
  | 'timeout'
  | 'config_error'
  | 'unauthorized'
  | 'bad_request'
  | 'not_found'
  | 'not_implemented'
  | 'internal_error';

export interface SerializedError {
  code: ErrorCode;
  message: string;
  details: Record<string, unknown>;
}

export class AppError extends Error {
  readonly code: ErrorCode;
  readonly statusCode: number;
  readonly details: Record<string, unknown>;

  constructor(
    code: ErrorCode,
    message: string,
    statusCode = 500,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = new.target.name;
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    // Restore prototype chain for instanceof checks when targeting ES5/ES2022.
    Object.setPrototypeOf(this, new.target.prototype);
  }

  toJSON(): SerializedError {
    return {
      code: this.code,
      message: this.message,
      details: this.details,
    };
  }
}

/** Configuration / environment validation failure (fatal at boot). */
export class ConfigError extends AppError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super('config_error', message, 500, details);
  }
}

/** Missing or invalid internal token (HTTP 403). */
export class UnauthorizedError extends AppError {
  constructor(message = 'Invalid or missing internal token.', details: Record<string, unknown> = {}) {
    super('unauthorized', message, 403, details);
  }
}

/** Malformed request: header/body mismatch or bad input (HTTP 400). */
export class BadRequestError extends AppError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super('bad_request', message, 400, details);
  }
}

/** Job payload failed schema validation (HTTP 400). */
export class InvalidPayloadError extends AppError {
  constructor(message = 'Invalid job payload.', details: Record<string, unknown> = {}) {
    super('invalid_payload', message, 400, details);
  }
}

/**
 * Job type is not supported by this renderer (HTTP 400).
 *
 * Decision: unknown job types are rejected up-front with a controlled 400 (the
 * job is never accepted), rather than accepting it and emitting a failed
 * callback — there is nothing to report back about a request we declined.
 */
export class UnsupportedJobTypeError extends AppError {
  constructor(jobType: string, details: Record<string, unknown> = {}) {
    super('unsupported_job_type', `Unsupported job_type: ${jobType}`, 400, {
      job_type: jobType,
      ...details,
    });
  }
}

/** Requested template_key is not registered and no fallback applies (HTTP 422). */
export class UnsupportedTemplateError extends AppError {
  constructor(templateKey: string, details: Record<string, unknown> = {}) {
    super('unsupported_template', `Unsupported template: ${templateKey}`, 422, {
      template_key: templateKey,
      ...details,
    });
  }
}

/** A render operation failed (HTTP 500). Reported to Django via `failed` callback. */
export class RenderFailedError extends AppError {
  constructor(message = 'Failed to render the requested asset.', details: Record<string, unknown> = {}) {
    super('render_failed', message, 500, details);
  }
}

/** Persisting a rendered file to storage failed (HTTP 500). */
export class StorageFailedError extends AppError {
  constructor(message = 'Failed to store the rendered file.', details: Record<string, unknown> = {}) {
    super('storage_failed', message, 500, details);
  }
}

/** Delivering the callback to Django failed (HTTP 502). */
export class CallbackFailedError extends AppError {
  constructor(message = 'Failed to deliver the callback.', details: Record<string, unknown> = {}) {
    super('callback_failed', message, 502, details);
  }
}

/** An operation exceeded its time budget (HTTP 504). */
export class TimeoutError extends AppError {
  constructor(message = 'Operation timed out.', details: Record<string, unknown> = {}) {
    super('timeout', message, 504, details);
  }
}

/** Resource not found (HTTP 404). */
export class NotFoundError extends AppError {
  constructor(message = 'Not found.', details: Record<string, unknown> = {}) {
    super('not_found', message, 404, details);
  }
}

/**
 * Feature scaffolded but not yet implemented in the current pipeline (HTTP 501).
 * Used by foundation-phase stubs that will be filled in by later pipelines.
 */
export class NotImplementedError extends AppError {
  constructor(feature: string, details: Record<string, unknown> = {}) {
    super('not_implemented', `Not implemented yet: ${feature}`, 501, {
      feature,
      ...details,
    });
  }
}

/** Narrows an unknown thrown value to an {@link AppError}, wrapping if needed. */
export function toAppError(err: unknown): AppError {
  if (err instanceof AppError) {
    return err;
  }

  // Map body-parser (express.json) errors to controlled responses.
  if (err && typeof err === 'object' && 'type' in err) {
    const type = (err as { type?: unknown }).type;
    if (type === 'entity.too.large') {
      return new AppError('invalid_payload', 'Job payload exceeds the maximum allowed size.', 413, {
        type,
      });
    }
    if (type === 'entity.parse.failed') {
      return new AppError('invalid_payload', 'Malformed JSON body.', 400, { type });
    }
  }

  const message = err instanceof Error ? err.message : 'Unexpected error.';
  return new AppError('internal_error', message, 500);
}
