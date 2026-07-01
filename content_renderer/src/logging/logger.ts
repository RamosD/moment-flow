/**
 * Minimal zero-dependency structured logger.
 *
 * Design goals (backlog CR-003):
 *  - Emit one JSON object per line so logs are machine-parseable.
 *  - Carry job correlation context (job_id, workspace_id, request_id, job_type,
 *    status) via child loggers.
 *  - NEVER print the internal token or any other secret. Sensitive keys are
 *    redacted recursively as defence-in-depth, in addition to the rule that
 *    callers must not pass secrets to the logger.
 *
 * A heavier engine (e.g. Pino) can be swapped in behind this same interface
 * later without touching call sites.
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_WEIGHT: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

const REDACTED = '[REDACTED]';
const MAX_REDACT_DEPTH = 8;

/**
 * Keys whose values must never be logged. Matched case-insensitively as a
 * substring, so this covers `INTERNAL_API_TOKEN`, `internalApiToken`,
 * `x-internal-token`, `authorization`, `apiKey`, etc.
 */
const SENSITIVE_KEY_PATTERN = /token|secret|password|authorization|api[-_]?key|credential/i;

export type LogFields = Record<string, unknown>;

export interface Logger {
  debug(message: string, fields?: LogFields): void;
  info(message: string, fields?: LogFields): void;
  warn(message: string, fields?: LogFields): void;
  error(message: string, fields?: LogFields): void;
  /** Returns a new logger with the given fields bound to every record. */
  child(bindings: LogFields): Logger;
}

export interface LoggerOptions {
  /** Minimum level to emit. Records below this are dropped. */
  level?: LogLevel;
  /** Fields bound to every record produced by this logger. */
  base?: LogFields;
  /**
   * Sink for a serialised log line. Defaults to stdout (stderr for `error`).
   * Injectable so tests can capture output.
   */
  write?: (line: string, level: LogLevel) => void;
}

function defaultWrite(line: string, level: LogLevel): void {
  if (level === 'error') {
    process.stderr.write(line + '\n');
  } else {
    process.stdout.write(line + '\n');
  }
}

/** Recursively replaces sensitive values with a redaction marker. */
export function redact(value: unknown, depth = 0): unknown {
  if (depth >= MAX_REDACT_DEPTH) {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => redact(item, depth + 1));
  }
  if (value !== null && typeof value === 'object') {
    if (value instanceof Error) {
      return { name: value.name, message: value.message };
    }
    const out: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
      out[key] = SENSITIVE_KEY_PATTERN.test(key) ? REDACTED : redact(val, depth + 1);
    }
    return out;
  }
  return value;
}

class StructuredLogger implements Logger {
  private readonly level: LogLevel;
  private readonly base: LogFields;
  private readonly write: (line: string, level: LogLevel) => void;

  constructor(options: LoggerOptions = {}) {
    this.level = options.level ?? 'info';
    this.base = options.base ?? {};
    this.write = options.write ?? defaultWrite;
  }

  private emit(level: LogLevel, message: string, fields?: LogFields): void {
    if (LEVEL_WEIGHT[level] < LEVEL_WEIGHT[this.level]) {
      return;
    }
    const record = {
      level,
      time: new Date().toISOString(),
      msg: message,
      ...this.base,
      ...(fields ?? {}),
    };
    const safe = redact(record);
    this.write(JSON.stringify(safe), level);
  }

  debug(message: string, fields?: LogFields): void {
    this.emit('debug', message, fields);
  }

  info(message: string, fields?: LogFields): void {
    this.emit('info', message, fields);
  }

  warn(message: string, fields?: LogFields): void {
    this.emit('warn', message, fields);
  }

  error(message: string, fields?: LogFields): void {
    this.emit('error', message, fields);
  }

  child(bindings: LogFields): Logger {
    return new StructuredLogger({
      level: this.level,
      base: { ...this.base, ...bindings },
      write: this.write,
    });
  }
}

export function createLogger(options: LoggerOptions = {}): Logger {
  return new StructuredLogger(options);
}

/**
 * Default application logger. Level defaults to `info` (or `LOG_LEVEL` when set),
 * and every record is tagged with the service name.
 */
export const logger: Logger = createLogger({
  level: (process.env.LOG_LEVEL as LogLevel) || 'info',
  base: { service: 'content_renderer' },
});
