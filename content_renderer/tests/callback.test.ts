import http from 'node:http';
import type { AddressInfo } from 'node:net';

import { describe, expect, it } from 'vitest';

import { createCallbackClient } from '../src/callbacks/callback.client';
import { buildCompletedPayload, buildFailedPayload } from '../src/callbacks/callback.payload';
import { loadConfig } from '../src/config/env';
import { createLogger } from '../src/logging/logger';
import type { AppConfig } from '../src/config/env';
import type { JobEnvelope } from '../src/jobs/job.types';

const TOKEN = 'super-secret-callback-token';

/**
 * Config with fast retries so the suite stays quick. Defaults to 3 attempts and
 * a 1ms base/5ms max backoff; individual tests override as needed.
 */
function configWith(overrides: Partial<AppConfig> = {}): AppConfig {
  return {
    ...loadConfig({ NODE_ENV: 'test', INTERNAL_API_TOKEN: TOKEN }),
    callbackMaxAttempts: 3,
    callbackRetryBaseDelayMs: 1,
    callbackRetryMaxDelayMs: 5,
    ...overrides,
  };
}

const envelope: JobEnvelope = {
  job_id: 'job-1',
  workspace_id: 'ws-1',
  request_id: 'req-1',
  job_type: 'content_generation',
  callback_url: 'http://placeholder/cb',
  entity: { type: 'content_pack_request', id: 'ent-1' },
  payload_version: '1.0',
  payload: {},
};

const completedPayload = () =>
  buildCompletedPayload(envelope, { status: 'completed', outputs: [] });

interface Received {
  headers: http.IncomingHttpHeaders;
  body: string;
}

interface TestServer {
  url: string;
  received: Received[];
  close: () => Promise<void>;
}

/**
 * Start a throwaway HTTP server. `respond` is called per request with the
 * response object and the 1-based request index, so a test can vary the
 * behaviour across retry attempts (e.g. fail the first, succeed the second).
 */
function startServer(
  respond: (res: http.ServerResponse, requestIndex: number) => void,
): Promise<TestServer> {
  return new Promise((resolve) => {
    const received: Received[] = [];
    const server = http.createServer((req, res) => {
      let body = '';
      req.on('data', (chunk) => {
        body += chunk;
      });
      req.on('end', () => {
        received.push({ headers: req.headers, body });
        respond(res, received.length);
      });
    });
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address() as AddressInfo;
      resolve({
        url: `http://127.0.0.1:${port}/callback`,
        received,
        close: () => new Promise<void>((done) => server.close(() => done())),
      });
    });
  });
}

const ok = (res: http.ServerResponse) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end('{}');
};

const status = (code: number) => (res: http.ServerResponse) => {
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end('{}');
};

describe('callback client — contract', () => {
  it('sends a completed payload following the Django contract (1st attempt)', async () => {
    const server = await startServer(ok);
    try {
      const client = createCallbackClient({
        config: configWith(),
        logger: createLogger({ write: () => {} }),
      });
      const payload = buildCompletedPayload(envelope, {
        status: 'completed',
        outputs: [{ output_type: 'post', format: 'png', status: 'completed' }],
      });

      const result = await client.send(server.url, payload);

      expect(result).toEqual({ ok: true, statusCode: 200, attempts: 1 });
      expect(server.received).toHaveLength(1);
      expect(server.received[0].headers['x-internal-token']).toBe(TOKEN);
      expect(server.received[0].headers['content-type']).toContain('application/json');

      const sent = JSON.parse(server.received[0].body);
      expect(sent).toMatchObject({ job_id: 'job-1', workspace_id: 'ws-1', status: 'completed', error: null });
      expect(sent.result.outputs[0].output_type).toBe('post');
    } finally {
      await server.close();
    }
  });

  it('sends a failed payload following the Django contract', async () => {
    const server = await startServer(ok);
    try {
      const client = createCallbackClient({
        config: configWith(),
        logger: createLogger({ write: () => {} }),
      });
      const payload = buildFailedPayload(envelope, {
        code: 'render_failed',
        message: 'Falha ao gerar o conteúdo.',
        details: {},
      });

      const result = await client.send(server.url, payload);

      expect(result.ok).toBe(true);
      const sent = JSON.parse(server.received[0].body);
      expect(sent).toMatchObject({ status: 'failed', result: null });
      expect(sent.error).toMatchObject({ code: 'render_failed', message: 'Falha ao gerar o conteúdo.' });
    } finally {
      await server.close();
    }
  });
});

describe('callback client — retry policy', () => {
  it('succeeds on the first attempt without retrying', async () => {
    const server = await startServer(ok);
    try {
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 3 }),
        logger: createLogger({ write: () => {} }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result.ok).toBe(true);
      expect(result.attempts).toBe(1);
      expect(server.received).toHaveLength(1);
    } finally {
      await server.close();
    }
  });

  it('retries after a transient failure and then succeeds', async () => {
    // First request 503, second request 200.
    const server = await startServer((res, i) => (i === 1 ? status(503)(res) : ok(res)));
    try {
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 3 }),
        logger: createLogger({ write: () => {} }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result).toEqual({ ok: true, statusCode: 200, attempts: 2 });
      expect(server.received).toHaveLength(2);
    } finally {
      await server.close();
    }
  });

  it('retries on HTTP 503 up to the limit, then reports a delivery failure', async () => {
    const server = await startServer(status(503));
    try {
      const lines: string[] = [];
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 3 }),
        logger: createLogger({ write: (line) => lines.push(line) }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result).toEqual({ ok: false, statusCode: 503, attempts: 3 });
      expect(server.received).toHaveLength(3);
      const output = lines.join('\n');
      expect(output).toContain('callback.retry_scheduled');
      expect(output).toContain('callback.delivery_failed');
      // Two retries were scheduled between the three attempts.
      expect(output.match(/callback\.attempt_started/g)).toHaveLength(3);
    } finally {
      await server.close();
    }
  });

  it('retries on timeout up to the limit', async () => {
    // Server never responds → each attempt aborts via AbortSignal.timeout.
    const server = await startServer(() => {
      /* intentionally no response */
    });
    try {
      const lines: string[] = [];
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 2, callbackTimeoutSeconds: 0.05 }),
        logger: createLogger({ write: (line) => lines.push(line) }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result.ok).toBe(false);
      expect(result.statusCode).toBe(0);
      expect(result.attempts).toBe(2);
      expect(lines.join('\n')).toContain('"reason":"timeout"');
    } finally {
      await server.close();
    }
  });

  it('does NOT retry on HTTP 400 (single attempt)', async () => {
    const server = await startServer(status(400));
    try {
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 3 }),
        logger: createLogger({ write: () => {} }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result).toEqual({ ok: false, statusCode: 400, attempts: 1 });
      expect(server.received).toHaveLength(1);
    } finally {
      await server.close();
    }
  });

  it('does NOT retry on HTTP 403 (single attempt)', async () => {
    const server = await startServer(status(403));
    try {
      const lines: string[] = [];
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 3 }),
        logger: createLogger({ write: (line) => lines.push(line) }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result).toEqual({ ok: false, statusCode: 403, attempts: 1 });
      expect(server.received).toHaveLength(1);
      const output = lines.join('\n');
      expect(output).toContain('"reason":"non_retryable_status"');
      expect(output).not.toContain('callback.retry_scheduled');
    } finally {
      await server.close();
    }
  });

  it('respects CALLBACK_MAX_ATTEMPTS exactly', async () => {
    const server = await startServer(status(502));
    try {
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 4 }),
        logger: createLogger({ write: () => {} }),
      });

      const result = await client.send(server.url, completedPayload());

      expect(result.attempts).toBe(4);
      expect(server.received).toHaveLength(4);
    } finally {
      await server.close();
    }
  });

  it('never logs the internal token across attempts', async () => {
    const server = await startServer((res, i) => (i === 1 ? status(503)(res) : ok(res)));
    try {
      const lines: string[] = [];
      const client = createCallbackClient({
        config: configWith({ callbackMaxAttempts: 3 }),
        logger: createLogger({ write: (line) => lines.push(line) }),
      });

      await client.send(server.url, completedPayload());

      const output = lines.join('\n');
      expect(output).not.toContain(TOKEN);
      expect(output).toContain('callback.attempt_started');
      expect(output).toContain('callback.completed');
    } finally {
      await server.close();
    }
  });
});
