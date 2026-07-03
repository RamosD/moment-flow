/**
 * E2E global teardown (STG-HARD-007) — redacts secrets from Playwright traces.
 *
 * Real finding from this same hardening pass: `trace: 'retain-on-failure'`
 * (playwright.config.ts) makes Playwright's browser-level network capture
 * record the *complete* request/response — including the `Authorization`
 * header (the JWT bearer token) on every authenticated call, and the literal
 * `{"email":..., "password":...}` body of the login request, in cleartext,
 * inside `trace.zip`. Neither is a bug in this suite's own code (nothing here
 * ever logs a token or the password) — it is exactly what a browser-level
 * network trace does by design. Left alone, a shared/retained `trace.zip`
 * would be the one artifact in this whole pipeline that *does* carry a
 * secret, contradicting the "never in artifacts" rule the rest of the stack
 * already follows (see `backend_core/apps/core/middleware.py`,
 * `integrations_bridge/clients.py`).
 *
 * This teardown runs after every E2E invocation (pass or fail — Playwright
 * guarantees `globalTeardown` always runs once `globalSetup` succeeded) and
 * rewrites every retained `test-results/**\/trace.zip` in place:
 *   - any `Authorization` / `Cookie` / `Set-Cookie` / `X-Internal-Token`
 *     header, on any request/response, is replaced with `[REDACTED]`;
 *   - the request body of a login/refresh call (`/auth/token/`,
 *     `/auth/token/refresh/`) and its response body (which carries the
 *     issued access/refresh tokens) are replaced wholesale — there is no
 *     legitimate diagnostic reason to keep the literal password or token
 *     value once the pass/fail signal for the *login step itself* is
 *     already captured by the test's own assertions and the (redacted)
 *     status code.
 *
 * Purely local: no network call, no cloud dependency, no new runtime
 * requirement beyond a small dev-only zip library.
 */
import { readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import AdmZip from 'adm-zip'

const here = path.dirname(fileURLToPath(import.meta.url))
const TEST_RESULTS_DIR = path.resolve(here, '..', 'test-results')

const SENSITIVE_HEADER_NAMES = new Set([
  'authorization',
  'cookie',
  'set-cookie',
  'x-internal-token',
])

// Endpoints whose entire request/response body is redacted outright (login
// credentials in, tokens out) rather than field-by-field — simpler and more
// robust than trying to enumerate every secret-bearing field shape.
const SENSITIVE_BODY_URL_MARKERS = ['/auth/token/', '/auth/token/refresh/']

interface HarHeader {
  name: string
  value: string
}

interface HarMessage {
  headers?: HarHeader[]
  postData?: { _sha1?: string }
  content?: { _sha1?: string }
}

interface NetworkSnapshotLine {
  snapshot?: { request?: HarMessage & { url?: string }; response?: HarMessage }
}

function redactHeaders(headers: HarHeader[] | undefined): boolean {
  if (!headers) return false
  let mutated = false
  for (const header of headers) {
    if (SENSITIVE_HEADER_NAMES.has(header.name.toLowerCase()) && header.value !== '[REDACTED]') {
      header.value = '[REDACTED]'
      mutated = true
    }
  }
  return mutated
}

/**
 * Redact one `*.network` JSONL file's content (headers + flag sensitive body
 * resource hashes for the caller to redact in a second pass over `resources/`
 * entries, since request/response bodies are stored as separate zip entries,
 * not inline).
 */
function redactNetworkFile(
  content: string,
  sensitiveHashes: Set<string>,
): { content: string; changed: boolean } {
  let changed = false
  const lines = content.split('\n').map((line) => {
    if (!line.trim()) return line
    let obj: NetworkSnapshotLine
    try {
      obj = JSON.parse(line)
    } catch {
      return line
    }
    const { request, response } = obj.snapshot ?? {}
    let mutated = false
    if (redactHeaders(request?.headers)) mutated = true
    if (redactHeaders(response?.headers)) mutated = true

    const url = request?.url ?? ''
    if (SENSITIVE_BODY_URL_MARKERS.some((marker) => url.includes(marker))) {
      const requestHash = request?.postData?._sha1
      const responseHash = response?.content?._sha1
      if (requestHash) sensitiveHashes.add(requestHash)
      if (responseHash) sensitiveHashes.add(responseHash)
    }

    if (!mutated) return line
    changed = true
    return JSON.stringify(obj)
  })
  return { content: lines.join('\n'), changed }
}

/** Redact one trace.zip in place. Returns true if anything was rewritten. */
function redactTraceZip(zipPath: string): boolean {
  const zip = new AdmZip(zipPath)
  const entries = zip.getEntries()
  const sensitiveHashes = new Set<string>()
  let changed = false

  for (const entry of entries) {
    if (!entry.entryName.endsWith('.network')) continue
    const original = entry.getData().toString('utf-8')
    const { content, changed: fileChanged } = redactNetworkFile(original, sensitiveHashes)
    if (fileChanged) {
      zip.updateFile(entry.entryName, Buffer.from(content, 'utf-8'))
      changed = true
    }
  }

  if (sensitiveHashes.size > 0) {
    for (const entry of entries) {
      if (!entry.entryName.startsWith('resources/')) continue
      const resourceName = entry.entryName.slice('resources/'.length)
      if (!sensitiveHashes.has(resourceName)) continue
      zip.updateFile(
        entry.entryName,
        Buffer.from('"[REDACTED — auth request/response body, STG-HARD-007]"', 'utf-8'),
      )
      changed = true
    }
  }

  if (changed) zip.writeZip(zipPath)
  return changed
}

function findTraceZips(dir: string): string[] {
  let results: string[] = []
  let entries: string[]
  try {
    entries = readdirSync(dir)
  } catch {
    return results
  }
  for (const entryName of entries) {
    const fullPath = path.join(dir, entryName)
    let info: ReturnType<typeof statSync>
    try {
      info = statSync(fullPath)
    } catch {
      continue
    }
    if (info.isDirectory()) {
      results = results.concat(findTraceZips(fullPath))
    } else if (entryName === 'trace.zip') {
      results.push(fullPath)
    }
  }
  return results
}

export default function globalTeardown(): void {
  const zipPaths = findTraceZips(TEST_RESULTS_DIR)
  let redactedCount = 0
  for (const zipPath of zipPaths) {
    try {
      if (redactTraceZip(zipPath)) redactedCount += 1
    } catch (err) {
      // Never fail the run over a redaction bug — but never stay silent
      // either: a trace that failed to redact must be treated as unsafe by
      // whoever finds it, so this is loud, not swallowed.
      console.warn(
        `[e2e] WARNING: failed to redact trace ${zipPath}: ` +
          `${err instanceof Error ? err.message : String(err)}. ` +
          'Treat this trace as potentially containing secrets — do not share it as-is.',
      )
    }
  }
  if (redactedCount > 0) {
    console.log(`[e2e] redacted secrets (Authorization/Cookie/auth bodies) from ${redactedCount} trace(s).`)
  }
}
