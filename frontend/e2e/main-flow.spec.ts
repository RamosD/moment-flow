import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

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

const ALLOWED_HOSTS = new Set([
  'localhost:5200',
  '127.0.0.1:5200',
  'localhost:8100',
  '127.0.0.1:8100',
])
const FORBIDDEN_PORTS = ['8201', '8202']

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

async function createActionFromFirstRecommendation(
  page: Page,
  actionType: 'manual_task' | 'report_request' | 'media_kit_request' | 'content_pack',
) {
  const item = firstRecommendationItem(page)
  await item.getByRole('button', { name: /^Create( another)? action$/ }).click()

  const dialog = page.getByRole('dialog').filter({ hasText: 'Create campaign action' })
  await dialog.getByLabel('Action type').selectOption(actionType)

  if (actionType === 'content_pack') {
    await dialog.getByLabel('Content pack').selectOption({ index: 1 })
  }

  await dialog.getByRole('button', { name: 'Create campaign action' }).click()
  await expect(dialog).toBeHidden()
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
    page = await browser.newPage()
    page.on('request', (request) => {
      const url = new URL(request.url())
      if (!url.protocol.startsWith('http')) return
      if (FORBIDDEN_PORTS.includes(url.port) || !ALLOWED_HOSTS.has(url.host)) {
        offBackendCoreRequests.push(request.url())
      }
    })
  })

  test.afterAll(async () => {
    await page.close()
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
