import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

/**
 * Seeds a disposable, namespaced dataset for this run via the Backend Core's
 * `seed_e2e_run` management command (see
 * `backend_core/apps/core/management/commands/seed_e2e_run.py`) — never via
 * a runtime mock, so every id the spec uses is real, backend-issued data.
 *
 * The run id is unique per invocation (timestamp + random suffix), so
 * repeated/parallel runs never collide and never require manual cleanup.
 * Non-secret ids are exposed to the spec via `process.env` (set for the test
 * process only, never written to a file); the password stays exactly where
 * the caller put it (`E2E_PASSWORD`) and is never logged or persisted.
 */
export default function globalSetup(): void {
  const password = process.env.E2E_PASSWORD
  if (!password) {
    throw new Error(
      'E2E_PASSWORD is not set. Export it before running the E2E suite — ' +
        'this harness never invents or hardcodes a password.',
    )
  }

  const runId = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
  const djangoDir = path.resolve(
    process.env.E2E_DJANGO_DIR ?? path.join(here, '..', '..', 'backend_core'),
  )
  const pythonBin =
    process.env.E2E_DJANGO_PYTHON ??
    (process.platform === 'win32'
      ? path.join(djangoDir, 'venv', 'Scripts', 'python.exe')
      : path.join(djangoDir, 'venv', 'bin', 'python'))

  if (!existsSync(pythonBin)) {
    throw new Error(
      `Django python interpreter not found at ${pythonBin}. Set ` +
        'E2E_DJANGO_PYTHON / E2E_DJANGO_DIR, or activate the backend_core venv layout expected by default.',
    )
  }

  const result = spawnSync(
    pythonBin,
    ['manage.py', 'seed_e2e_run', `--run-id=${runId}`],
    { cwd: djangoDir, env: process.env, encoding: 'utf-8' },
  )

  if (result.status !== 0) {
    throw new Error(
      `seed_e2e_run failed (exit ${result.status}).\n--- stdout ---\n${result.stdout}\n--- stderr ---\n${result.stderr}`,
    )
  }

  const lastLine = result.stdout.trim().split('\n').pop() ?? ''
  let seeded: {
    run_id: string
    email: string
    workspace_id: string
    workspace_name: string
    artist_id: string
    campaign_id: string
  }
  try {
    seeded = JSON.parse(lastLine)
  } catch {
    throw new Error(`seed_e2e_run did not print the expected JSON line: ${lastLine}`)
  }

  process.env.E2E_RUN_ID = seeded.run_id
  process.env.E2E_EMAIL = seeded.email
  process.env.E2E_WORKSPACE_ID = seeded.workspace_id
  process.env.E2E_CAMPAIGN_ID = seeded.campaign_id
}
