import { describe, expect, it } from 'vitest';
import request from 'supertest';

import { createApp } from '../src/app';
import { loadConfig } from '../src/config/env';
import { RENDERER_NAME, RENDERER_VERSION } from '../src/constants';
import { createLogger } from '../src/logging/logger';

function buildTestApp() {
  const config = loadConfig({
    NODE_ENV: 'test',
    INTERNAL_API_TOKEN: 'test-token',
  });
  // Silent logger so the test output stays clean.
  const logger = createLogger({ write: () => {} });
  return createApp(config, { logger });
}

describe('GET /health', () => {
  it('returns 200 with service identity', async () => {
    const app = buildTestApp();

    const res = await request(app).get('/health');

    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      status: 'ok',
      service: RENDERER_NAME,
      version: RENDERER_VERSION,
    });
    expect(typeof res.body.uptime_seconds).toBe('number');
    expect(typeof res.body.timestamp).toBe('string');
  });

  it('returns a normalised 404 for unknown routes', async () => {
    const app = buildTestApp();

    const res = await request(app).get('/does-not-exist');

    expect(res.status).toBe(404);
    expect(res.body.error).toMatchObject({ code: 'not_found' });
  });
});
