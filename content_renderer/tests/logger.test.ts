import { describe, expect, it } from 'vitest';

import { createLogger, redact } from '../src/logging/logger';

const SECRET = 'super-secret-internal-token-value';

function capture() {
  const lines: string[] = [];
  const logger = createLogger({
    level: 'debug',
    base: { service: 'content_renderer' },
    write: (line) => lines.push(line),
  });
  return { logger, lines };
}

describe('logger redaction', () => {
  it('never prints INTERNAL_API_TOKEN-style fields', () => {
    const { logger, lines } = capture();

    logger.info('job.received', {
      job_id: 'job-1',
      INTERNAL_API_TOKEN: SECRET,
      internalApiToken: SECRET,
      headers: { 'x-internal-token': SECRET, authorization: `Bearer ${SECRET}` },
    });

    const output = lines.join('\n');
    expect(output).not.toContain(SECRET);
    expect(output).toContain('[REDACTED]');
    // Non-sensitive context is preserved.
    expect(output).toContain('job-1');
  });

  it('redacts secrets bound via child loggers', () => {
    const { logger, lines } = capture();

    const child = logger.child({ token: SECRET, request_id: 'req-9' });
    child.warn('callback.prepare');

    const output = lines.join('\n');
    expect(output).not.toContain(SECRET);
    expect(output).toContain('req-9');
  });

  it('emits one JSON object per line with level and message', () => {
    const { logger, lines } = capture();

    logger.info('server.started', { port: 8002 });

    expect(lines).toHaveLength(1);
    const parsed = JSON.parse(lines[0]);
    expect(parsed).toMatchObject({ level: 'info', msg: 'server.started', port: 8002 });
    expect(typeof parsed.time).toBe('string');
  });

  it('redact() deeply replaces sensitive keys without touching safe ones', () => {
    const result = redact({
      job_id: 'abc',
      nested: { api_key: SECRET, keep: 'ok' },
      list: [{ secret: SECRET }],
    }) as Record<string, unknown>;

    const serialised = JSON.stringify(result);
    expect(serialised).not.toContain(SECRET);
    expect(serialised).toContain('abc');
    expect(serialised).toContain('ok');
  });
});
