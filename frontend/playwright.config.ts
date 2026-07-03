import { defineConfig, devices } from '@playwright/test'

/**
 * E2E config for the main login → War Room → CampaignActions flow
 * (STG-PRE-009). Requires the real Backend Core (and, for a real
 * `source=engine` intelligence step, the real Intelligence Engine) already
 * running — see `e2e/global-setup.ts` and
 * `frontend/docs/01_fundamentos/05_staging_operacionalizacao_pre_producao/resultados_execucao/prompt_09_e2e_automatizado_resultado.md`
 * for the exact pre-conditions and how to run this locally.
 *
 * Nothing here starts Backend Core, the Intelligence Engine or the Content
 * Renderer — they are independent services with their own lifecycle
 * (matches the runbook: this project never lets a test runner own
 * cross-service orchestration). Only the frontend dev server is optionally
 * managed, and only if one isn't already listening on the target port.
 */
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:5200'

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  // Redacts Authorization/Cookie headers and login request/response bodies
  // from every retained trace.zip — see `e2e/global-teardown.ts` for why this
  // is needed (STG-HARD-007). Always runs, pass or fail.
  globalTeardown: './e2e/global-teardown.ts',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  // `list` for terminal readability (unchanged — the quality gate only
  // checks the process exit code, never parses this output). `html`
  // (STG-HARD-007) persists a browsable report under `playwright-report/`
  // that surfaces screenshots, traces *and* custom `testInfo.attach()`
  // diagnostics (see `e2e/diagnostics.ts`) as clickable items — without it,
  // a custom attachment's body only lives zipped inside `trace.zip`, one
  // `show-trace` away from being found. `open: 'never'`: local-only, never
  // auto-launches a browser (matters for `-WithE2E` in the quality gate).
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'pnpm dev',
    url: baseURL,
    reuseExistingServer: true,
    timeout: 30_000,
  },
})
