/**
 * Environment configuration loader (backlog CR-002).
 *
 * `loadConfig` is a pure function of its `source` (defaults to `process.env`),
 * which makes the validation rules straightforward to unit-test. It is the only
 * place that interprets raw environment variables.
 *
 * Token rules:
 *  - production: INTERNAL_API_TOKEN must be non-empty, otherwise boot fails.
 *  - development: an empty token is rejected UNLESS the operator explicitly
 *    opts into insecure local mode via ALLOW_INSECURE_EMPTY_TOKEN=true.
 *  - test: an empty token is allowed so the suite can run without secrets.
 */
import { config as loadDotenv } from 'dotenv';

import { ConfigError } from '../errors/errors';
import type { StorageProviderName } from '../storage/storage.types';

// Populate process.env from a local .env file if present. This is a no-op when
// the file is absent, and never overrides variables already set in the
// environment. Passing an explicit `source` to loadConfig bypasses this.
// `quiet` suppresses dotenv's promotional banner so logs stay clean structured JSON.
loadDotenv({ quiet: true });

export type NodeEnv = 'development' | 'production' | 'test';

/**
 * Preferred output format for `report_generation`:
 *  - `auto` (default): generate a PDF, falling back to HTML if PDF generation
 *    is unavailable or fails;
 *  - `pdf`: same as `auto` (PDF preferred, HTML as a safety fallback);
 *  - `html`: skip PDF entirely and emit HTML (for constrained environments).
 */
export type ReportOutputFormat = 'auto' | 'pdf' | 'html';

export interface AppConfig {
  nodeEnv: NodeEnv;
  port: number;
  internalApiToken: string;
  allowInsecureEmptyToken: boolean;
  insecureTokenMode: boolean;
  rendererPublicBaseUrl: string;
  backendCoreBaseUrl: string;
  storageProvider: StorageProviderName;
  localStorageRoot: string;
  localStoragePublicBaseUrl: string;
  /** S3-compatible storage config (STG-LOCAL-004). Only required when storageProvider === 's3'. */
  storageEndpoint: string;
  storageBucket: string;
  storageRegion: string;
  storageAccessKey: string;
  storageSecretKey: string;
  storageForcePathStyle: boolean;
  /** Public base URL for downloads; defaults to `<endpoint>/<bucket>` (path-style) when unset. */
  storagePublicBaseUrl: string;
  maxJobPayloadBytes: number;
  callbackTimeoutSeconds: number;
  renderTimeoutSeconds: number;
  reportOutputFormat: ReportOutputFormat;
  /** Max callback delivery attempts (>= 1). 1 disables retry. */
  callbackMaxAttempts: number;
  /** Base backoff delay between callback attempts, in ms (>= 0). */
  callbackRetryBaseDelayMs: number;
  /** Upper bound for the backoff delay, in ms (>= base delay). */
  callbackRetryMaxDelayMs: number;
}

function parseNodeEnv(raw: string | undefined): NodeEnv {
  const value = (raw ?? 'development').trim().toLowerCase();
  if (value === 'development' || value === 'production' || value === 'test') {
    return value;
  }
  throw new ConfigError(
    `Invalid NODE_ENV "${raw}". Expected one of: development, production, test.`,
    { variable: 'NODE_ENV' },
  );
}

function parseBoolean(raw: string | undefined, fallback: boolean): boolean {
  if (raw === undefined || raw.trim() === '') {
    return fallback;
  }
  const value = raw.trim().toLowerCase();
  if (['true', '1', 'yes', 'on'].includes(value)) return true;
  if (['false', '0', 'no', 'off'].includes(value)) return false;
  throw new ConfigError(`Invalid boolean for value "${raw}". Use true/false.`);
}

function parsePositiveInteger(name: string, raw: string | undefined, fallback: number): number {
  if (raw === undefined || raw.trim() === '') {
    return fallback;
  }
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) {
    throw new ConfigError(`Invalid ${name}: expected a positive integer, got "${raw}".`, {
      variable: name,
    });
  }
  return value;
}

/**
 * Parse an integer that must be >= `min` (allows 0, unlike
 * {@link parsePositiveInteger}). Used for retry tuning where a base delay of 0
 * is valid.
 */
function parseIntegerAtLeast(
  name: string,
  raw: string | undefined,
  fallback: number,
  min: number,
): number {
  if (raw === undefined || raw.trim() === '') {
    return fallback;
  }
  const value = Number(raw);
  if (!Number.isInteger(value) || value < min) {
    throw new ConfigError(`Invalid ${name}: expected an integer >= ${min}, got "${raw}".`, {
      variable: name,
    });
  }
  return value;
}

function stringOrDefault(raw: string | undefined, fallback: string): string {
  const value = (raw ?? '').trim();
  return value === '' ? fallback : value;
}

/** Known storage providers implemented behind {@link StorageProvider}. */
const KNOWN_STORAGE_PROVIDERS: readonly StorageProviderName[] = ['local', 's3'];

function parseStorageProvider(raw: string | undefined): StorageProviderName {
  const value = (raw ?? 'local').trim().toLowerCase();
  if (value === '') {
    return 'local';
  }
  if ((KNOWN_STORAGE_PROVIDERS as readonly string[]).includes(value)) {
    return value as StorageProviderName;
  }
  throw new ConfigError(
    `Invalid STORAGE_PROVIDER "${raw}". Expected one of: ${KNOWN_STORAGE_PROVIDERS.join(', ')}.`,
    { variable: 'STORAGE_PROVIDER' },
  );
}

function parseReportOutputFormat(raw: string | undefined): ReportOutputFormat {
  const value = (raw ?? 'auto').trim().toLowerCase();
  if (value === '') {
    return 'auto';
  }
  if (value === 'auto' || value === 'pdf' || value === 'html') {
    return value;
  }
  throw new ConfigError(
    `Invalid REPORT_OUTPUT_FORMAT "${raw}". Expected one of: auto, pdf, html.`,
    { variable: 'REPORT_OUTPUT_FORMAT' },
  );
}

function validateInternalToken(args: {
  nodeEnv: NodeEnv;
  internalApiToken: string;
  allowInsecureEmptyToken: boolean;
}): void {
  const { nodeEnv, internalApiToken, allowInsecureEmptyToken } = args;
  if (internalApiToken !== '') {
    return;
  }

  if (nodeEnv === 'production') {
    throw new ConfigError(
      'INTERNAL_API_TOKEN is required and must not be empty in production.',
      { variable: 'INTERNAL_API_TOKEN' },
    );
  }

  if (nodeEnv === 'development' && !allowInsecureEmptyToken) {
    throw new ConfigError(
      'INTERNAL_API_TOKEN is empty. Set INTERNAL_API_TOKEN, or explicitly enable ' +
        'insecure local mode with ALLOW_INSECURE_EMPTY_TOKEN=true (development only).',
      { variable: 'INTERNAL_API_TOKEN' },
    );
  }
  // test: empty token permitted.
}

/**
 * Validate the S3-compatible storage config (STG-LOCAL-004). Only enforced
 * when `storageProvider === 's3'` — the `local` provider (dev default) never
 * requires these variables. Fails fast at boot, mirroring
 * {@link validateInternalToken}. Error details never include the secret key
 * value itself, only the variable name.
 */
function validateStorageConfig(args: {
  storageProvider: StorageProviderName;
  storageEndpoint: string;
  storageBucket: string;
  storageAccessKey: string;
  storageSecretKey: string;
}): void {
  if (args.storageProvider !== 's3') {
    return;
  }
  const required: Array<[string, string]> = [
    ['STORAGE_ENDPOINT', args.storageEndpoint],
    ['STORAGE_BUCKET', args.storageBucket],
    ['STORAGE_ACCESS_KEY', args.storageAccessKey],
    ['STORAGE_SECRET_KEY', args.storageSecretKey],
  ];
  for (const [name, value] of required) {
    if (value.trim() === '') {
      throw new ConfigError(`${name} is required when STORAGE_PROVIDER=s3.`, { variable: name });
    }
  }
}

/**
 * Build and validate the application configuration from a raw environment map.
 * Throws {@link ConfigError} on any invalid or missing-required value.
 */
export function loadConfig(source: NodeJS.ProcessEnv = process.env): AppConfig {
  const nodeEnv = parseNodeEnv(source.NODE_ENV);
  const allowInsecureEmptyToken = parseBoolean(source.ALLOW_INSECURE_EMPTY_TOKEN, false);
  const internalApiToken = (source.INTERNAL_API_TOKEN ?? '').trim();

  validateInternalToken({ nodeEnv, internalApiToken, allowInsecureEmptyToken });

  const insecureTokenMode = internalApiToken === '';

  // Callback retry tuning (R-HARD-006). Validated up-front so a misconfiguration
  // fails fast at boot rather than at the first callback.
  const callbackMaxAttempts = parseIntegerAtLeast(
    'CALLBACK_MAX_ATTEMPTS',
    source.CALLBACK_MAX_ATTEMPTS,
    3,
    1,
  );
  const callbackRetryBaseDelayMs = parseIntegerAtLeast(
    'CALLBACK_RETRY_BASE_DELAY_MS',
    source.CALLBACK_RETRY_BASE_DELAY_MS,
    500,
    0,
  );
  const callbackRetryMaxDelayMs = parseIntegerAtLeast(
    'CALLBACK_RETRY_MAX_DELAY_MS',
    source.CALLBACK_RETRY_MAX_DELAY_MS,
    5000,
    0,
  );
  if (callbackRetryMaxDelayMs < callbackRetryBaseDelayMs) {
    throw new ConfigError(
      `Invalid CALLBACK_RETRY_MAX_DELAY_MS: must be >= CALLBACK_RETRY_BASE_DELAY_MS ` +
        `(${callbackRetryBaseDelayMs}), got ${callbackRetryMaxDelayMs}.`,
      { variable: 'CALLBACK_RETRY_MAX_DELAY_MS' },
    );
  }

  const storageProvider = parseStorageProvider(source.STORAGE_PROVIDER);
  const storageEndpoint = (source.STORAGE_ENDPOINT ?? '').trim();
  const storageBucket = (source.STORAGE_BUCKET ?? '').trim();
  const storageAccessKey = (source.STORAGE_ACCESS_KEY ?? '').trim();
  const storageSecretKey = (source.STORAGE_SECRET_KEY ?? '').trim();
  validateStorageConfig({
    storageProvider,
    storageEndpoint,
    storageBucket,
    storageAccessKey,
    storageSecretKey,
  });
  // Path-style addressing (http://endpoint/bucket/key) is required for MinIO
  // and most self-hosted S3-compatible endpoints, which don't support
  // virtual-hosted-style (http://bucket.endpoint/key) DNS resolution.
  const storageForcePathStyle = parseBoolean(source.STORAGE_FORCE_PATH_STYLE, true);
  const storagePublicBaseUrlRaw = (source.STORAGE_PUBLIC_BASE_URL ?? '').trim();
  const storagePublicBaseUrl =
    storagePublicBaseUrlRaw !== ''
      ? storagePublicBaseUrlRaw.replace(/\/+$/, '')
      : storageEndpoint !== '' && storageBucket !== ''
        ? `${storageEndpoint.replace(/\/+$/, '')}/${storageBucket}`
        : '';

  return {
    nodeEnv,
    port: parsePositiveInteger('PORT', source.PORT, 8202),
    internalApiToken,
    allowInsecureEmptyToken,
    insecureTokenMode,
    rendererPublicBaseUrl: stringOrDefault(
      source.RENDERER_PUBLIC_BASE_URL,
      'http://localhost:8202',
    ),
    backendCoreBaseUrl: stringOrDefault(source.BACKEND_CORE_BASE_URL, 'http://localhost:8100'),
    storageProvider,
    localStorageRoot: stringOrDefault(source.LOCAL_STORAGE_ROOT, './storage'),
    localStoragePublicBaseUrl: stringOrDefault(
      source.LOCAL_STORAGE_PUBLIC_BASE_URL,
      'http://localhost:8202/files',
    ),
    storageEndpoint,
    storageBucket,
    storageRegion: stringOrDefault(source.STORAGE_REGION, 'us-east-1'),
    storageAccessKey,
    storageSecretKey,
    storageForcePathStyle,
    storagePublicBaseUrl,
    maxJobPayloadBytes: parsePositiveInteger(
      'MAX_JOB_PAYLOAD_BYTES',
      source.MAX_JOB_PAYLOAD_BYTES,
      1_048_576,
    ),
    callbackTimeoutSeconds: parsePositiveInteger(
      'CALLBACK_TIMEOUT_SECONDS',
      source.CALLBACK_TIMEOUT_SECONDS,
      20,
    ),
    renderTimeoutSeconds: parsePositiveInteger(
      'RENDER_TIMEOUT_SECONDS',
      source.RENDER_TIMEOUT_SECONDS,
      30,
    ),
    reportOutputFormat: parseReportOutputFormat(source.REPORT_OUTPUT_FORMAT),
    callbackMaxAttempts,
    callbackRetryBaseDelayMs,
    callbackRetryMaxDelayMs,
  };
}
