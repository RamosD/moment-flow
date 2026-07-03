/**
 * E2E diagnostics helper (STG-HARD-007).
 *
 * On a failing step, screenshots and traces (already configured in
 * `playwright.config.ts` — `screenshot: 'only-on-failure'`,
 * `trace: 'retain-on-failure'`) show *what the browser saw*, but not *what the
 * backend/renderer were doing at the same time*. This module closes that gap
 * locally, with no cloud dependency: it reads the same four log files the
 * runbook already points operators at
 * (`.local-runtime/logs/{backend_core.err,intelligence_engine.out,
 * content_renderer.out,frontend.out}.log`), keeps only the lines that mention
 * a correlation id / run id seen during the failing test, redacts anything
 * secret-shaped as a defensive second layer (the services themselves already
 * never log these — see `backend_core/apps/core/middleware.py` and
 * `integrations_bridge/clients.py` — this is belt-and-braces, not the primary
 * control), and attaches the result to the Playwright report as JSON.
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { TestInfo } from '@playwright/test'

const here = path.dirname(fileURLToPath(import.meta.url))
const LOG_DIR = path.resolve(here, '..', '..', '.local-runtime', 'logs')

// Same four files documented in the runbook (§14/§18) — one per local
// service. Kept as a literal list (not a directory scan) so a stray unrelated
// file in `.local-runtime/logs/` is never accidentally attached.
const LOG_FILES = [
  'backend_core.err.log',
  'intelligence_engine.out.log',
  'content_renderer.out.log',
  'frontend.out.log',
] as const

// Defensive redaction — a second layer on top of the services' own logging
// discipline (which already never writes these). Never trust a single layer
// for secrets.
const SECRET_PATTERNS: RegExp[] = [
  /Authorization:\s*Bearer\s+\S+/gi,
  /X-Internal-Token:\s*\S+/gi,
  /INTERNAL_API_TOKEN=\S+/gi,
  /E2E_PASSWORD=\S+/gi,
  /STORAGE_SECRET_KEY=\S+/gi,
  /STORAGE_ACCESS_KEY=\S+/gi,
  /"password"\s*:\s*"[^"]*"/gi,
]

function redact(line: string): string {
  return SECRET_PATTERNS.reduce((acc, pattern) => acc.replace(pattern, '[REDACTED]'), line)
}

export interface LogExcerptOptions {
  /** Correlation/request ids (and the run id) to filter log lines by. */
  ids: string[]
  /** Lines to keep per file when none of `ids` matches anything (a tail, not the whole file). */
  tailLines?: number
}

/**
 * Read, filter and redact the four local service logs.
 *
 * Filters by `ids` when at least one is non-empty; otherwise falls back to
 * the last `tailLines` lines so a failure still carries *some* recent
 * context instead of nothing. Never reads more than one file's worth of
 * content per service, and never throws — a missing/rotated log file
 * degrades to a clear placeholder string, never an attachment failure.
 */
export function collectLogExcerpts({ ids, tailLines = 40 }: LogExcerptOptions): Record<string, string> {
  const meaningfulIds = ids.filter((id): id is string => Boolean(id && id.length > 0))
  const excerpts: Record<string, string> = {}

  for (const fileName of LOG_FILES) {
    const filePath = path.join(LOG_DIR, fileName)
    let raw: string
    try {
      raw = readFileSync(filePath, 'utf-8')
    } catch {
      excerpts[fileName] = '(not found — service may not have been running, or logs were cleared)'
      continue
    }
    const lines = raw.split(/\r?\n/)
    const matched =
      meaningfulIds.length > 0
        ? lines.filter((line) => meaningfulIds.some((id) => line.includes(id)))
        : []
    const chosen = matched.length > 0 ? matched : lines.slice(-tailLines)
    excerpts[fileName] = chosen.map(redact).join('\n')
  }
  return excerpts
}

export interface DiagnosticsContext {
  runId?: string
  /** Correlation/request ids observed during the test (e.g. from `X-Request-ID` response headers). */
  ids: string[]
  /** Any extra, non-secret context worth attaching (endpoint hit counts, workspace/campaign ids, …). */
  extra?: Record<string, unknown>
}

/**
 * Attach filtered, redacted local-log excerpts plus run context to the
 * current (failing) test. Call from an `afterEach` guarded by
 * `testInfo.status !== testInfo.expectedStatus` — this is diagnostic
 * evidence, not a substitute for the test's own assertions.
 */
export async function attachDiagnostics(testInfo: TestInfo, context: DiagnosticsContext): Promise<void> {
  const excerpts = collectLogExcerpts({ ids: [context.runId ?? '', ...context.ids] })
  const body = JSON.stringify(
    {
      run_id: context.runId ?? null,
      correlation_ids: context.ids,
      extra: context.extra ?? {},
      logs: excerpts,
    },
    null,
    2,
  )
  await testInfo.attach('e2e-diagnostics', { body, contentType: 'application/json' })
}
