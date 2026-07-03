import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

import { attachDiagnostics } from './diagnostics.js'

/**
 * Main pre-production flow (STG-PRE-009): login, War Room with real/controlled
 * intelligence, the four CampaignAction creation paths, mark reviewed, dismiss,
 * CampaignActionsPanel content, reload persistence, and a Backend-Core-only
 * network assertion.
 *
 * Data comes from `global-setup.ts` (a namespaced `seed_e2e_run` per run) —
 * nothing here is a runtime mock; every request hits the real Backend Core.
 * Creating a manual task / report / media kit / content pack action is only
 * reachable in this UI from a recommendation card's "Create action" dialog
 * (there is no standalone "new action" affordance), so this suite requires
 * Intelligence to return at least one recommendation. A freshly seeded,
 * empty campaign already gets real recommendations from a *real* Intelligence
 * Engine (heuristics like "no media kit exists yet" fire immediately), but
 * `INTELLIGENCE_ENGINE_DRY_RUN=true` always returns zero recommendations —
 * see the report for this exact pre-condition.
 *
 * All steps share one `page` (a single browser context created once in
 * `beforeAll`) rather than the per-test `page` fixture: the access token
 * lives only in an in-memory ref (`AuthProvider`), so a fresh context per
 * step would silently drop the session between steps.
 */

const EMAIL = process.env.E2E_EMAIL
const PASSWORD = process.env.E2E_PASSWORD
const CAMPAIGN_ID = process.env.E2E_CAMPAIGN_ID
const RUN_ID = process.env.E2E_RUN_ID
const WORKSPACE_ID = process.env.E2E_WORKSPACE_ID

const ALLOWED_HOSTS = new Set([
  'localhost:5200',
  '127.0.0.1:5200',
  'localhost:8100',
  '127.0.0.1:8100',
])
const FORBIDDEN_PORTS = ['8201', '8202']

/**
 * Trim an id down to its last 8 characters for a console/annotation line —
 * still enough to eyeball-correlate against a log grep, but not the full
 * workspace/campaign UUID echoed verbatim into console output for no
 * functional reason (the full id is always available from `process.env.*`
 * to any code path that actually needs it, e.g. `page.goto`).
 */
function shortId(id: string | undefined): string {
  if (!id) return 'unknown'
  return id.length > 8 ? `…${id.slice(-8)}` : id
}

// Correlation ids (`X-Request-ID`, see `trackedPost` below) observed across
// the whole run — shared so a failing step's diagnostics can be correlated
// against everything the suite did up to that point, not just its own call.
const correlationIds: string[] = []
// Backend Core endpoints actually hit during this run (method + pathname,
// never query strings/bodies) — a quick "what did the suite even do" summary
// attached on failure, per STG-HARD-007 ("endpoints de backend usados").
const endpointHits = new Map<string, number>()

function recommendationsSection(page: Page) {
  return page.locator('section', {
    has: page.getByRole('heading', { name: 'Recommendations', level: 2 }),
  })
}

function campaignActionsSection(page: Page) {
  return page.locator('section', {
    has: page.getByRole('heading', { name: 'Campaign Actions', level: 2 }),
  })
}

function firstRecommendationItem(page: Page) {
  return recommendationsSection(page).getByRole('listitem').first()
}

type ActionType = 'manual_task' | 'report_request' | 'media_kit_request' | 'content_pack'

// report_request / media_kit_request / content_pack each create an artifact
// first (POST /reports/, /media-kits/, /content-pack-requests/). All three
// artifact endpoints synchronously submit an external render job to the
// Content Renderer inside the same Django request/response cycle
// (`create_and_submit_external_job`, see
// `backend_core/apps/integrations_bridge/services.py`), gated by
// `REPORT_RENDERER_TIMEOUT_SECONDS` / `CONTENT_RENDERER_TIMEOUT_SECONDS`
// (30s by default, `backend_core/config/settings.py`). So the artifact POST can
// legitimately take close to 30s if the renderer is briefly slow to accept the
// job — that is the most likely explanation for the STG-LOCAL-008 media-kit
// flake (dialog stuck on "Creating…" past the suite's default 10s expect
// timeout while a follow-up direct API call was fast again seconds later).
// `manual_task` has no artifact step and keeps the suite's default timeout.
const ARTIFACT_POST_PATH: Partial<Record<ActionType, string>> = {
  report_request: '/reports/',
  media_kit_request: '/media-kits/',
  content_pack: '/content-pack-requests/',
}
const ARTIFACT_NETWORK_TIMEOUT_MS = 35_000

interface TrackedRequest {
  url: string
  status: number
  requestId: string | null
  durationMs: number
}

/**
 * Wait for the real HTTP response of the given POST (a real signal — not a
 * sleep, not a UI poll) and return enough of it for diagnostics: status,
 * `X-Request-ID` (the correlation id threaded through Backend
 * Core/Renderer logs, see `backend_core/apps/core/middleware.py`) and how long
 * it actually took.
 */
async function trackedPost(page: Page, pathSuffix: string): Promise<TrackedRequest> {
  const startedAt = Date.now()
  const response = await page.waitForResponse(
    (candidate) =>
      candidate.request().method() === 'POST' && candidate.url().includes(pathSuffix),
    { timeout: ARTIFACT_NETWORK_TIMEOUT_MS },
  )
  const requestId = response.headers()['x-request-id'] ?? null
  if (requestId) correlationIds.push(requestId)
  return {
    url: response.url(),
    status: response.status(),
    requestId,
    durationMs: Date.now() - startedAt,
  }
}

async function createActionFromFirstRecommendation(page: Page, actionType: ActionType) {
  const item = firstRecommendationItem(page)
  await item.getByRole('button', { name: /^Create( another)? action$/ }).click()

  const dialog = page.getByRole('dialog').filter({ hasText: 'Create campaign action' })
  await dialog.getByLabel('Action type').selectOption(actionType)

  if (actionType === 'content_pack') {
    await dialog.getByLabel('Content pack').selectOption({ index: 1 })
  }

  const artifactPath = ARTIFACT_POST_PATH[actionType]
  // Registered (listener attached) before the click — never after — so a
  // response that arrives immediately after the click is never missed.
  const artifactWait = artifactPath ? trackedPost(page, artifactPath) : null
  const campaignActionWait = trackedPost(page, '/campaign-actions/')

  await dialog.getByRole('button', { name: 'Create campaign action' }).click()

  const observed: TrackedRequest[] = []
  try {
    if (artifactWait) observed.push(await artifactWait)
    observed.push(await campaignActionWait)
    // Both real network responses are already in by this point, so the
    // dialog closing is just a React state update away — the suite's default
    // expect timeout (10s) is unchanged and untouched here.
    await expect(dialog).toBeHidden()
  } catch (err) {
    test.info().annotations.push({
      type: 'e2e-diagnostic',
      description:
        `createAction(${actionType}) did not complete as expected. ` +
        `Requests observed: ${JSON.stringify(observed)}. ` +
        'Cross-reference the requestId(s) above with Backend Core / Content ' +
        'Renderer logs (.local-runtime/logs/) for this run.',
    })
    throw err
  }

  test.info().annotations.push({
    type: 'e2e-timing',
    description: `createAction(${actionType}): ${JSON.stringify(observed)}`,
  })
}

test.describe.configure({ mode: 'serial' })

test.describe('main flow: login → War Room → CampaignActions → persistence', () => {
  let page: Page
  let recommendationTitle = ''
  const offBackendCoreRequests: string[] = []

  test.beforeAll(async ({ browser }) => {
    if (!EMAIL || !PASSWORD || !CAMPAIGN_ID) {
      throw new Error(
        'E2E_EMAIL / E2E_PASSWORD / E2E_CAMPAIGN_ID missing — global-setup did not run, or E2E_PASSWORD was not exported before `playwright test`.',
      )
    }
    // Printed once, to `list`-reporter stdout: the minimum an operator needs
    // to go find this run's data/logs without re-deriving it from scratch
    // (STG-HARD-007 — "run-id usado", "endpoints de backend usados" below).
    // Never the password/token — only ids that are already namespacing, not
    // secret, identifiers (see seed_e2e_run.py).
    console.log(
      `[e2e] run_id=${RUN_ID ?? 'unknown'} workspace=${shortId(WORKSPACE_ID)} ` +
        `campaign=${shortId(CAMPAIGN_ID)} email=${EMAIL}`,
    )
    page = await browser.newPage()
    page.on('request', (request) => {
      const url = new URL(request.url())
      if (!url.protocol.startsWith('http')) return
      if (ALLOWED_HOSTS.has(url.host)) {
        const key = `${request.method()} ${url.pathname}`
        endpointHits.set(key, (endpointHits.get(key) ?? 0) + 1)
      }
      if (FORBIDDEN_PORTS.includes(url.port) || !ALLOWED_HOSTS.has(url.host)) {
        offBackendCoreRequests.push(request.url())
      }
    })
  })

  test.afterAll(async () => {
    await page.close()
  })

  // Diagnostic evidence only — never a substitute for the assertions above.
  // Runs after every test; attaches nothing when the test passed.
  // Playwright requires the first parameter to be an object-destructuring
  // pattern (it inspects the signature to resolve fixtures); no fixture is
  // needed here besides `page`, which the outer `describe` already shares.
  // eslint-disable-next-line no-empty-pattern
  test.afterEach(async ({}, testInfo) => {
    if (testInfo.status === testInfo.expectedStatus) return
    await attachDiagnostics(testInfo, {
      runId: RUN_ID,
      ids: correlationIds,
      extra: {
        failed_test: testInfo.title,
        workspace_id: WORKSPACE_ID ?? null,
        campaign_id: CAMPAIGN_ID ?? null,
        endpoint_hits: Object.fromEntries(endpointHits),
      },
    })
  })

  test('login', async () => {
    await page.goto('/login')
    await page.getByLabel('Email').fill(EMAIL!)
    await page.getByLabel('Password').fill(PASSWORD!)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page).toHaveURL('/')
    await expect(page.getByText(EMAIL!)).toBeVisible()
  })

  test('open campaign and War Room', async () => {
    await page.goto(`/campaigns/${CAMPAIGN_ID}`)
    await page.getByRole('button', { name: 'Open War Room' }).click()
    await expect(page).toHaveURL(new RegExp(`/campaigns/${CAMPAIGN_ID}/war-room$`))
  })

  test('intelligence executes and yields at least one recommendation', async () => {
    await expect(recommendationsSection(page)).toBeVisible()
    await expect(firstRecommendationItem(page)).toBeVisible({ timeout: 20_000 })
    recommendationTitle = (
      await firstRecommendationItem(page).locator('span').first().innerText()
    ).trim()
    expect(recommendationTitle.length).toBeGreaterThan(0)
  })

  test('create manual task action from the recommendation', async () => {
    await createActionFromFirstRecommendation(page, 'manual_task')
  })

  test('create report action from the recommendation', async () => {
    await createActionFromFirstRecommendation(page, 'report_request')
  })

  test('create media kit action from the recommendation', async () => {
    await createActionFromFirstRecommendation(page, 'media_kit_request')
  })

  test('create content pack action from the recommendation', async () => {
    await createActionFromFirstRecommendation(page, 'content_pack')
  })

  test('mark reviewed on the recommendation', async () => {
    await firstRecommendationItem(page)
      .getByRole('button', { name: 'Mark reviewed' })
      .click()
    await expect(
      firstRecommendationItem(page).getByRole('button', { name: 'Reviewed' }),
    ).toBeVisible()
  })

  test('dismiss the recommendation', async () => {
    await firstRecommendationItem(page).getByRole('button', { name: 'Dismiss' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Dismiss recommendation' })
    await dialog
      .getByLabel('Dismiss reason')
      .fill('E2E main-flow: exercising the dismiss path.')
    await dialog.getByRole('button', { name: 'Dismiss recommendation' }).click()
    await expect(dialog).toBeHidden()
  })

  test('CampaignActionsPanel lists every action created against this recommendation', async () => {
    const matches = campaignActionsSection(page)
      .getByRole('listitem')
      .filter({ hasText: recommendationTitle })
    // Logged before the assertion so the actual count is captured in the
    // report even if the expectation below fails (STG-HARD-007 — "número de
    // acções encontradas").
    const foundCount = await matches.count()
    test.info().annotations.push({
      type: 'e2e-actions-found',
      description: `found=${foundCount} expected=6`,
    })
    // manual_task, report_request, media_kit_request, content_pack, mark_reviewed, dismiss.
    await expect(matches).toHaveCount(6)
  })

  test('reload: every action persists (real backend, not client cache)', async () => {
    await page.reload()
    const matches = campaignActionsSection(page)
      .getByRole('listitem')
      .filter({ hasText: recommendationTitle })
    await expect(matches).toHaveCount(6)

    const dismissed = matches.filter({ hasText: 'Dismiss ·' })
    await expect(dismissed).toHaveCount(1)
    await expect(dismissed.getByText('Dismissed', { exact: true })).toBeVisible()

    const reviewed = matches.filter({ hasText: 'Mark reviewed ·' })
    await expect(reviewed).toHaveCount(1)
    await expect(reviewed.getByText('Completed', { exact: true })).toBeVisible()
  })

  test('the frontend only ever talked to the Backend Core', () => {
    expect(offBackendCoreRequests).toEqual([])
  })
})
