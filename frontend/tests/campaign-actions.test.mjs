import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { mapHttpError } from '../src/shared/api/error-mapping.ts'
import {
  ForbiddenError,
  NetworkError,
  NotFoundError,
  ServiceUnavailableError,
  UnauthorizedError,
  ValidationError,
} from '../src/shared/api/errors.ts'
import { appendSafeCustomHeaders } from '../src/shared/api/security.ts'
import { resolveErrorPreset } from '../src/shared/ui/states/error-presets.ts'
import {
  campaignActionStatusLabel,
  campaignActionTypeLabel,
  relatedArtifactStatusLabel,
  relatedArtifactStatusVariant,
} from '../src/entities/campaign-action/helpers.ts'
import {
  availablePanelTransitions,
  buildCampaignActionRetryPayload,
} from '../src/entities/campaign-action/lifecycle.ts'
import {
  deriveRecommendationRef,
  MAX_RECOMMENDATION_REF_LENGTH,
} from '../src/entities/campaign-action/recommendation-ref.ts'
import { sanitizeCampaignActionWritePayload } from '../src/entities/campaign-action/write-payload.ts'
import {
  buildRecommendationSnapshot,
  MAX_RECOMMENDATION_SNAPSHOT_BYTES,
  normalizeCampaignActionPriority,
} from '../src/features/campaign-actions/recommendation-snapshot.ts'
import { buildRecommendationDecisionPayload } from '../src/features/campaign-actions/recommendation-decision-payload.ts'
import {
  findActiveRecommendationAction,
  groupCampaignActionsByRecommendationRef,
  matchRecommendationActions,
  recommendationActionDisplayState,
  recommendationExecutionState,
} from '../src/features/campaign-actions/recommendation-action-match.ts'

const CAMPAIGN_ID = '00000000-0000-4000-8000-000000000001'
const WORKSPACE_ID = '00000000-0000-4000-8000-000000000002'

function action(overrides = {}) {
  return {
    id: crypto.randomUUID(),
    workspace: WORKSPACE_ID,
    campaign: CAMPAIGN_ID,
    recommendation_ref: 'recommendation:one',
    recommendation_snapshot: { title: 'Recommendation' },
    title: 'Action',
    description: 'Description',
    action_type: 'manual_task',
    status: 'pending',
    priority: 'medium',
    source: 'recommendation',
    dismiss_reason: '',
    metadata: {},
    related_content_pack_request: null,
    related_content_output: null,
    related_report: null,
    related_media_kit: null,
    created_by: null,
    completed_at: null,
    cancelled_at: null,
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-01T12:00:00Z',
    ...overrides,
  }
}

function draft(ref = 'recommendation:one') {
  return {
    recommendationRef: {
      ref,
      campaignId: CAMPAIGN_ID,
      index: 0,
      recommendationId: null,
      title: 'Recommendation',
      action: null,
      type: null,
    },
    recommendationSnapshot: { title: 'Recommendation' },
    title: 'Recommendation',
    description: 'Because it matters',
    priority: 'high',
    confidence: 0.8,
    suggestedActionType: null,
    source: 'recommendation',
  }
}

test('status and action type labels use the persistent enums', () => {
  assert.equal(campaignActionStatusLabel('in_progress'), 'In progress')
  assert.equal(campaignActionStatusLabel('dismissed'), 'Dismissed')
  assert.equal(campaignActionTypeLabel('mark_reviewed'), 'Mark reviewed')
  assert.equal(campaignActionTypeLabel('media_kit_request'), 'Media kit')
})

test('related artifact status surfaces the linked entity, not the action, as failed', () => {
  // STG-PRE-007: MediaKit has no dedicated FAILED status of its own, so the
  // API derives "failed" from metadata — the frontend label/variant must
  // treat it exactly like a Report's real "failed" status.
  assert.equal(
    relatedArtifactStatusLabel({ type: 'report', status: 'failed' }),
    'Report: failed',
  )
  assert.equal(
    relatedArtifactStatusLabel({ type: 'media_kit', status: 'failed' }),
    'Media kit: failed',
  )
  assert.equal(
    relatedArtifactStatusLabel({
      type: 'content_pack_request',
      status: 'partially_completed',
    }),
    'Content pack: partially completed',
  )
  assert.equal(relatedArtifactStatusVariant('failed'), 'danger')
  assert.equal(relatedArtifactStatusVariant('completed'), 'success')
  assert.equal(relatedArtifactStatusVariant('queued'), 'neutral')
})

test('priority normalisation covers enum-like, numeric and fallback values', () => {
  assert.equal(normalizeCampaignActionPriority('critical'), 'urgent')
  assert.equal(normalizeCampaignActionPriority('HIGH'), 'high')
  assert.equal(normalizeCampaignActionPriority(1), 'low')
  assert.equal(normalizeCampaignActionPriority(3), 'high')
  assert.equal(normalizeCampaignActionPriority(undefined), 'medium')
})

test('snapshot is allowlisted, recursively sanitized and size bounded', () => {
  const snapshot = buildRecommendationSnapshot({
    title: 'Safe title',
    reason: {
      safe: 'kept',
      token: 'must-not-survive',
      nested: { private_key: 'hidden', note: 'kept too' },
    },
    priority: 'urgent',
    unexpected: 'not allowlisted',
  })

  assert.equal(snapshot.title, 'Safe title')
  assert.equal(snapshot.priority, 'urgent')
  assert.equal(snapshot.unexpected, undefined)
  assert.deepEqual(JSON.parse(JSON.stringify(snapshot.reason)), {
    safe: 'kept',
    nested: { note: 'kept too' },
  })
  assert.ok(
    new TextEncoder().encode(JSON.stringify(snapshot)).byteLength <
      MAX_RECOMMENDATION_SNAPSHOT_BYTES,
  )
})

test('recommendation ref prefers id and never exceeds the backend limit', () => {
  const byId = deriveRecommendationRef(
    CAMPAIGN_ID,
    { id: `rec-${'x'.repeat(700)}`, title: 'Ignored fallback' },
    4,
  )
  assert.match(byId.ref, /:id:/)
  assert.ok(byId.ref.length <= MAX_RECOMMENDATION_REF_LENGTH)

  const fallback = deriveRecommendationRef(
    CAMPAIGN_ID,
    { title: 'Release campaign report' },
    4,
  )
  assert.match(fallback.ref, /:i4:release-campaign-report$/)
})

test('write payload sanitizer strips workspace without mutating input', () => {
  const input = {
    workspace: WORKSPACE_ID,
    campaign: CAMPAIGN_ID,
    title: 'Safe',
  }
  const result = sanitizeCampaignActionWritePayload(input)

  assert.equal('workspace' in result, false)
  assert.equal(input.workspace, WORKSPACE_ID)
  assert.notEqual(result, input)
})

test('decision payloads omit client-owned status/workspace and trim dismiss reason', () => {
  const reviewed = buildRecommendationDecisionPayload({
    action_type: 'mark_reviewed',
    campaign: CAMPAIGN_ID,
    draft: draft(),
  })
  assert.equal(reviewed.action_type, 'mark_reviewed')
  assert.equal('status' in reviewed, false)
  assert.equal('workspace' in reviewed, false)
  assert.equal('metadata' in reviewed, false)

  const dismissed = buildRecommendationDecisionPayload({
    action_type: 'dismiss',
    campaign: CAMPAIGN_ID,
    draft: draft(),
    dismiss_reason: '  no longer relevant  ',
  })
  assert.equal(dismissed.action_type, 'dismiss')
  assert.equal(dismissed.dismiss_reason, 'no longer relevant')
  assert.equal('status' in dismissed, false)
})

test('matching groups multiple actions and deduplicates only active same type', () => {
  const report = action({ action_type: 'report_request', status: 'completed' })
  const failedReport = action({ action_type: 'report_request', status: 'failed' })
  const mediaKit = action({ action_type: 'media_kit_request', status: 'pending' })
  const other = action({ recommendation_ref: 'recommendation:two' })
  const actions = [report, failedReport, mediaKit, other]

  const grouped = groupCampaignActionsByRecommendationRef(actions)
  assert.equal(grouped.get('recommendation:one').length, 3)
  assert.deepEqual(matchRecommendationActions(draft(), actions), actions.slice(0, 3))
  assert.equal(
    findActiveRecommendationAction(actions, 'report_request'),
    report,
  )
  assert.equal(
    findActiveRecommendationAction([failedReport], 'report_request'),
    undefined,
  )
  assert.equal(
    findActiveRecommendationAction(actions, 'media_kit_request'),
    mediaKit,
  )
})

test('reviewed and dismissed remain distinct recommendation states', () => {
  const reviewed = action({
    action_type: 'mark_reviewed',
    status: 'completed',
  })
  const dismissed = action({ action_type: 'dismiss', status: 'dismissed' })
  const cancelled = action({ status: 'cancelled' })

  assert.equal(recommendationActionDisplayState(reviewed), 'reviewed')
  assert.equal(recommendationActionDisplayState(dismissed), 'dismissed')
  assert.equal(recommendationExecutionState([reviewed]), 'reviewed')
  assert.equal(recommendationExecutionState([dismissed]), 'dismissed')
  assert.equal(recommendationExecutionState([cancelled]), 'cancelled')
})

test('panel transition helper mirrors terminal backend lifecycle', () => {
  assert.deepEqual(availablePanelTransitions('pending'), [
    'complete',
    'cancel',
    'dismiss',
  ])
  assert.deepEqual(availablePanelTransitions('in_progress'), [
    'complete',
    'cancel',
  ])
  for (const terminal of ['completed', 'failed', 'dismissed', 'cancelled']) {
    assert.deepEqual(availablePanelTransitions(terminal), [])
  }
})

test('failed retry creates a new payload with formal compatible relations', () => {
  const failed = action({
    action_type: 'content_pack',
    status: 'failed',
    related_content_pack_request: '00000000-0000-4000-8000-000000000010',
    related_content_output: '00000000-0000-4000-8000-000000000011',
  })
  const payload = buildCampaignActionRetryPayload(failed)

  assert.equal(payload.action_type, 'content_pack')
  assert.equal(
    payload.related_content_pack_request,
    failed.related_content_pack_request,
  )
  assert.equal(payload.related_content_output, failed.related_content_output)
  assert.equal('id' in payload, false)
  assert.equal('status' in payload, false)
  assert.equal('completed_at' in payload, false)
  assert.equal(buildCampaignActionRetryPayload(action()), null)
})

test('provider-owned auth, workspace and internal headers cannot be overridden', () => {
  const headers = new Headers()
  let blocked = 0
  appendSafeCustomHeaders(
    {
      'X-Internal-Token': 'must-not-be-sent',
      Authorization: 'must-not-be-sent',
      'X-Workspace-ID': 'foreign-workspace',
      'X-Request-ID': 'safe-request-id',
    },
    headers,
    () => {
      blocked += 1
    },
  )

  assert.equal(headers.has('X-Internal-Token'), false)
  assert.equal(headers.has('Authorization'), false)
  assert.equal(headers.has('X-Workspace-ID'), false)
  assert.equal(headers.get('X-Request-ID'), 'safe-request-id')
  assert.equal(blocked, 3)
})

test('HTTP mapping preserves validation, auth, permission and hidden-resource classes', () => {
  const validation = mapHttpError(
    new Response(null, { status: 400 }),
    { recommendation_ref: ['Already exists.'] },
  )
  assert.ok(validation instanceof ValidationError)
  assert.deepEqual(validation.fieldErrors, {
    recommendation_ref: ['Already exists.'],
  })
  assert.ok(
    mapHttpError(new Response(null, { status: 401 }), {}) instanceof
      UnauthorizedError,
  )
  assert.ok(
    mapHttpError(new Response(null, { status: 403 }), {}) instanceof
      ForbiddenError,
  )
  assert.ok(
    mapHttpError(new Response(null, { status: 404 }), {}) instanceof
      NotFoundError,
  )
  assert.ok(
    mapHttpError(new Response(null, { status: 503 }), {}) instanceof
      ServiceUnavailableError,
  )
})

test('public presets keep 403 distinct and 404 disclosure-neutral', () => {
  const forbidden = resolveErrorPreset(
    new ForbiddenError('backend detail', {}),
  )
  const notFound = resolveErrorPreset(new NotFoundError('secret object', {}))
  const network = resolveErrorPreset(new NetworkError('offline'))
  const unavailable = resolveErrorPreset(
    new ServiceUnavailableError('upstream detail', { status: 503 }),
  )

  assert.equal(forbidden.title, 'Access denied')
  assert.notEqual(forbidden.title, notFound.title)
  assert.equal(notFound.title, 'Not found')
  assert.equal(notFound.description.includes('secret object'), false)
  assert.equal(network.title, 'Connection problem')
  assert.equal(unavailable.title, 'Service unavailable')
})

test('partial-success retry structurally never recreates the artifact', async () => {
  const source = await readFile(
    new URL(
      '../src/features/campaign-actions/useCreateActionFromRecommendation.ts',
      import.meta.url,
    ),
    'utf8',
  )
  const createArtifactIndex = source.indexOf(
    'const artifact = await createArtifact(input)',
  )
  const registerActionIndex = source.indexOf(
    'const campaignAction = await createCampaignAction(campaignActionPayload)',
    createArtifactIndex,
  )
  assert.ok(createArtifactIndex >= 0)
  assert.ok(registerActionIndex > createArtifactIndex)
  assert.match(
    source.slice(registerActionIndex),
    /throw new CampaignActionPartialSuccessError/,
  )

  const retryStart = source.indexOf(
    'async function retryCampaignActionRegistration',
  )
  const retryEnd = source.indexOf('/** Orchestrate', retryStart)
  const retryBlock = source.slice(retryStart, retryEnd)
  assert.match(retryBlock, /fetchCampaignActions/)
  assert.match(retryBlock, /createCampaignAction\(payload\)/)
  assert.doesNotMatch(retryBlock, /createArtifact\(/)
  assert.doesNotMatch(retryBlock, /createContentPackRequest\(/)
  assert.doesNotMatch(retryBlock, /createReport\(/)
  assert.doesNotMatch(retryBlock, /createMediaKit\(/)
})
