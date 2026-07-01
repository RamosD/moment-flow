import { describe, expect, it } from 'vitest';

import { loadConfig } from '../src/config/env';
import { ConfigError } from '../src/errors/errors';

const BASE = {
  PORT: '8002',
  RENDERER_PUBLIC_BASE_URL: 'http://localhost:8002',
  BACKEND_CORE_BASE_URL: 'http://localhost:8000',
  LOCAL_STORAGE_ROOT: './storage',
  LOCAL_STORAGE_PUBLIC_BASE_URL: 'http://localhost:8002/files',
  MAX_JOB_PAYLOAD_BYTES: '1048576',
  CALLBACK_TIMEOUT_SECONDS: '20',
  RENDER_TIMEOUT_SECONDS: '30',
};

describe('loadConfig', () => {
  it('parses a valid development configuration with a token', () => {
    const config = loadConfig({
      ...BASE,
      NODE_ENV: 'development',
      INTERNAL_API_TOKEN: 'dev-secret',
    });

    expect(config.nodeEnv).toBe('development');
    expect(config.port).toBe(8002);
    expect(config.internalApiToken).toBe('dev-secret');
    expect(config.insecureTokenMode).toBe(false);
    expect(config.maxJobPayloadBytes).toBe(1_048_576);
    expect(config.callbackTimeoutSeconds).toBe(20);
    expect(config.renderTimeoutSeconds).toBe(30);
  });

  it('applies sensible defaults when optional vars are missing', () => {
    const config = loadConfig({
      NODE_ENV: 'test',
      INTERNAL_API_TOKEN: 'x',
    });

    expect(config.port).toBe(8002);
    expect(config.rendererPublicBaseUrl).toBe('http://localhost:8002');
    expect(config.backendCoreBaseUrl).toBe('http://localhost:8000');
    expect(config.localStorageRoot).toBe('./storage');
    expect(config.maxJobPayloadBytes).toBe(1_048_576);
    // Storage provider default (R-HARD-005).
    expect(config.storageProvider).toBe('local');
    // Callback retry defaults (R-HARD-006).
    expect(config.callbackMaxAttempts).toBe(3);
    expect(config.callbackRetryBaseDelayMs).toBe(500);
    expect(config.callbackRetryMaxDelayMs).toBe(5000);
  });

  it('parses valid callback retry configuration', () => {
    const config = loadConfig({
      ...BASE,
      NODE_ENV: 'test',
      INTERNAL_API_TOKEN: 'x',
      CALLBACK_MAX_ATTEMPTS: '5',
      CALLBACK_RETRY_BASE_DELAY_MS: '0',
      CALLBACK_RETRY_MAX_DELAY_MS: '0',
    });

    expect(config.callbackMaxAttempts).toBe(5);
    expect(config.callbackRetryBaseDelayMs).toBe(0);
    expect(config.callbackRetryMaxDelayMs).toBe(0);
  });

  it('rejects CALLBACK_MAX_ATTEMPTS below 1', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'test', INTERNAL_API_TOKEN: 'x', CALLBACK_MAX_ATTEMPTS: '0' }),
    ).toThrow(ConfigError);
  });

  it('rejects a non-integer CALLBACK_MAX_ATTEMPTS', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'test', INTERNAL_API_TOKEN: 'x', CALLBACK_MAX_ATTEMPTS: '2.5' }),
    ).toThrow(ConfigError);
  });

  it('rejects a negative CALLBACK_RETRY_BASE_DELAY_MS', () => {
    expect(() =>
      loadConfig({
        ...BASE,
        NODE_ENV: 'test',
        INTERNAL_API_TOKEN: 'x',
        CALLBACK_RETRY_BASE_DELAY_MS: '-1',
      }),
    ).toThrow(ConfigError);
  });

  it('rejects CALLBACK_RETRY_MAX_DELAY_MS smaller than the base delay', () => {
    expect(() =>
      loadConfig({
        ...BASE,
        NODE_ENV: 'test',
        INTERNAL_API_TOKEN: 'x',
        CALLBACK_RETRY_BASE_DELAY_MS: '1000',
        CALLBACK_RETRY_MAX_DELAY_MS: '500',
      }),
    ).toThrow(ConfigError);
  });

  it('rejects an empty INTERNAL_API_TOKEN in production', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'production', INTERNAL_API_TOKEN: '' }),
    ).toThrow(ConfigError);
  });

  it('rejects whitespace-only INTERNAL_API_TOKEN in production', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'production', INTERNAL_API_TOKEN: '   ' }),
    ).toThrow(ConfigError);
  });

  it('rejects an empty token in development without the insecure opt-in', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'development', INTERNAL_API_TOKEN: '' }),
    ).toThrow(ConfigError);
  });

  it('allows an empty token in development only with ALLOW_INSECURE_EMPTY_TOKEN=true', () => {
    const config = loadConfig({
      ...BASE,
      NODE_ENV: 'development',
      INTERNAL_API_TOKEN: '',
      ALLOW_INSECURE_EMPTY_TOKEN: 'true',
    });

    expect(config.internalApiToken).toBe('');
    expect(config.insecureTokenMode).toBe(true);
    expect(config.allowInsecureEmptyToken).toBe(true);
  });

  it('throws on a non-numeric PORT', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'test', INTERNAL_API_TOKEN: 'x', PORT: 'not-a-number' }),
    ).toThrow(ConfigError);
  });

  it('throws on an invalid NODE_ENV', () => {
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'staging', INTERNAL_API_TOKEN: 'x' }),
    ).toThrow(ConfigError);
  });

  it('accepts STORAGE_PROVIDER=local and rejects unknown providers', () => {
    expect(
      loadConfig({ ...BASE, NODE_ENV: 'test', INTERNAL_API_TOKEN: 'x', STORAGE_PROVIDER: 'local' })
        .storageProvider,
    ).toBe('local');
    expect(() =>
      loadConfig({ ...BASE, NODE_ENV: 'test', INTERNAL_API_TOKEN: 'x', STORAGE_PROVIDER: 's3' }),
    ).toThrow(ConfigError);
  });
});
