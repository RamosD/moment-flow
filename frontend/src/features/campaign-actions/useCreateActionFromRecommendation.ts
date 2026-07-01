import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'

import {
  createCampaignAction,
  fetchCampaignActions,
  invalidateCampaignActionCache,
  updateCampaignAction,
} from '@/entities/campaign-action'
import type {
  CampaignAction,
  CreateCampaignActionPayload,
  CreateContentPackCampaignActionPayload,
  CreateDismissCampaignActionPayload,
  CreateManualTaskCampaignActionPayload,
  CreateMarkReviewedCampaignActionPayload,
  CreateMediaKitCampaignActionPayload,
  CreateReportCampaignActionPayload,
  UpdateCampaignActionPayload,
} from '@/entities/campaign-action'
import {
  contentPackRequestKeys,
  createContentPackRequest,
} from '@/entities/content-pack-request'
import { createMediaKit, mediaKitKeys } from '@/entities/media-kit'
import { createReport, reportKeys } from '@/entities/report'
import type { ReportType } from '@/entities/report'
import type { UUID } from '@/shared/types'

type UnlinkedContentPackAction = Omit<
  CreateContentPackCampaignActionPayload,
  'related_content_pack_request' | 'related_content_output'
>

type UnlinkedReportAction = Omit<
  CreateReportCampaignActionPayload,
  'related_report'
>

type UnlinkedMediaKitAction = Omit<
  CreateMediaKitCampaignActionPayload,
  'related_media_kit'
>

type ArtifactlessActionPayload =
  | CreateManualTaskCampaignActionPayload
  | CreateMarkReviewedCampaignActionPayload
  | CreateDismissCampaignActionPayload

export type CreateActionFromRecommendationInput =
  | {
      mode: 'create'
      campaignAction: ArtifactlessActionPayload
    }
  | {
      mode: 'create'
      campaignAction: UnlinkedContentPackAction
      artifact: {
        content_pack: UUID
        artist?: UUID | null
        track?: UUID | null
      }
    }
  | {
      mode: 'create'
      campaignAction: UnlinkedReportAction
      artifact: {
        report_type?: ReportType
        artist?: UUID | null
        track?: UUID | null
      }
    }
  | {
      mode: 'create'
      campaignAction: UnlinkedMediaKitAction
      artifact: {
        artist: UUID
        track?: UUID | null
      }
    }

export type CreatedArtifactReference =
  | {
      kind: 'content_pack_request'
      id: UUID
      workspace: UUID
      campaign: UUID | null
    }
  | {
      kind: 'report'
      id: UUID
      workspace: UUID
      campaign: UUID | null
    }
  | {
      kind: 'media_kit'
      id: UUID
      workspace: UUID
      campaign: UUID | null
    }

export interface PartialCampaignActionCreation {
  artifact: CreatedArtifactReference
  campaignActionPayload: CreateCampaignActionPayload
}

export class CampaignActionPartialSuccessError extends Error {
  readonly partial: PartialCampaignActionCreation
  readonly retryable: boolean

  constructor(
    message: string,
    partial: PartialCampaignActionCreation,
    options: { cause: unknown; retryable: boolean },
  ) {
    super(message, { cause: options.cause })
    this.name = 'CampaignActionPartialSuccessError'
    this.partial = partial
    this.retryable = options.retryable
  }
}

export interface RetryCampaignActionRegistrationInput {
  mode: 'retry_campaign_action'
  partial: PartialCampaignActionCreation
}

export type CreateActionFromRecommendationMutationInput =
  | CreateActionFromRecommendationInput
  | RetryCampaignActionRegistrationInput

type ArtifactActionInput = Exclude<
  CreateActionFromRecommendationInput,
  { campaignAction: ArtifactlessActionPayload }
>

export interface CreateActionFromRecommendationResult {
  campaignAction: CampaignAction
  artifact: CreatedArtifactReference | null
  recoveredExistingAction: boolean
}

const ACTIVE_DUPLICATE_STATUSES = new Set([
  'pending',
  'in_progress',
  'completed',
])

function artifactRelationPayload(
  artifact: CreatedArtifactReference,
): UpdateCampaignActionPayload {
  switch (artifact.kind) {
    case 'content_pack_request':
      return { related_content_pack_request: artifact.id }
    case 'report':
      return { related_report: artifact.id }
    case 'media_kit':
      return { related_media_kit: artifact.id }
  }
}

function actionRelationId(
  action: CampaignAction,
  artifact: CreatedArtifactReference,
): UUID | null {
  switch (artifact.kind) {
    case 'content_pack_request':
      return action.related_content_pack_request
    case 'report':
      return action.related_report
    case 'media_kit':
      return action.related_media_kit
  }
}

function withArtifactRelation(
  payload:
    | UnlinkedContentPackAction
    | UnlinkedReportAction
    | UnlinkedMediaKitAction,
  artifact: CreatedArtifactReference,
): CreateCampaignActionPayload {
  return { ...payload, ...artifactRelationPayload(artifact) } as
    CreateCampaignActionPayload
}

function assertArtifactScope(
  artifact: CreatedArtifactReference,
  workspaceId: string,
  campaignId: UUID,
  payload: CreateCampaignActionPayload,
): void {
  if (
    artifact.workspace === workspaceId &&
    artifact.campaign === campaignId
  ) {
    return
  }

  throw new CampaignActionPartialSuccessError(
    'The artifact was created, but its workspace/campaign does not match the CampaignAction.',
    { artifact, campaignActionPayload: payload },
    {
      cause: new Error('Artifact scope mismatch.'),
      retryable: false,
    },
  )
}

function invalidateArtifactCache(
  queryClient: QueryClient,
  workspaceId: string,
  artifact: CreatedArtifactReference,
): Promise<unknown> {
  switch (artifact.kind) {
    case 'content_pack_request':
      return queryClient.invalidateQueries({
        queryKey: contentPackRequestKeys.byCampaign(
          workspaceId,
          artifact.campaign ?? '',
        ),
      })
    case 'report':
      return queryClient.invalidateQueries({
        queryKey: reportKeys.byCampaign(workspaceId, artifact.campaign ?? ''),
      })
    case 'media_kit':
      return queryClient.invalidateQueries({
        queryKey: mediaKitKeys.byCampaign(
          workspaceId,
          artifact.campaign ?? '',
        ),
      })
  }
}

async function invalidateBestEffort(promise: Promise<unknown>): Promise<void> {
  try {
    await promise
  } catch {
    // Cache refresh failure must not turn a completed write into a retryable
    // business failure; later navigation/refetch still converges the cache.
  }
}

async function createArtifact(
  input: ArtifactActionInput,
): Promise<CreatedArtifactReference> {
  const { campaignAction } = input
  switch (campaignAction.action_type) {
    case 'content_pack': {
      if (!('artifact' in input) || !('content_pack' in input.artifact)) {
        throw new Error('Content pack request input is incomplete.')
      }
      const artifact = await createContentPackRequest({
        campaign: campaignAction.campaign,
        content_pack: input.artifact.content_pack,
        artist: input.artifact.artist,
        track: input.artifact.track,
      })
      return {
        kind: 'content_pack_request',
        id: artifact.id,
        workspace: artifact.workspace,
        campaign: artifact.campaign,
      }
    }
    case 'report_request': {
      if (!('artifact' in input)) throw new Error('Report input is incomplete.')
      const artifact = await createReport({
        campaign: campaignAction.campaign,
        title: campaignAction.title,
        report_type:
          'report_type' in input.artifact
            ? input.artifact.report_type
            : undefined,
        artist: input.artifact.artist,
        track: input.artifact.track,
      })
      return {
        kind: 'report',
        id: artifact.id,
        workspace: artifact.workspace,
        campaign: artifact.campaign ?? null,
      }
    }
    case 'media_kit_request': {
      const artist = 'artifact' in input ? input.artifact.artist : undefined
      if (typeof artist !== 'string' || !artist) {
        throw new Error('Media kit input is incomplete.')
      }
      const artifact = await createMediaKit({
        campaign: campaignAction.campaign,
        title: campaignAction.title,
        artist,
        track: input.artifact.track,
      })
      return {
        kind: 'media_kit',
        id: artifact.id,
        workspace: artifact.workspace,
        campaign: artifact.campaign ?? null,
      }
  }
}
}

async function createTwoStepAction(
  input: ArtifactActionInput,
  workspaceId: string,
  queryClient: QueryClient,
): Promise<CreateActionFromRecommendationResult> {
  const artifact = await createArtifact(input)
  await invalidateBestEffort(
    invalidateArtifactCache(queryClient, workspaceId, artifact),
  )

  const campaignActionPayload = withArtifactRelation(
    input.campaignAction,
    artifact,
  )
  assertArtifactScope(
    artifact,
    workspaceId,
    input.campaignAction.campaign,
    campaignActionPayload,
  )

  try {
    const campaignAction = await createCampaignAction(campaignActionPayload)
    await invalidateBestEffort(
      invalidateCampaignActionCache(queryClient, workspaceId, campaignAction),
    )
    return {
      campaignAction,
      artifact,
      recoveredExistingAction: false,
    }
  } catch (cause) {
    throw new CampaignActionPartialSuccessError(
      'The artifact was created, but CampaignAction registration failed.',
      { artifact, campaignActionPayload },
      { cause, retryable: true },
    )
  }
}

async function reconcileExistingAction(
  action: CampaignAction,
  partial: PartialCampaignActionCreation,
): Promise<CampaignAction> {
  const currentRelation = actionRelationId(action, partial.artifact)
  if (currentRelation === partial.artifact.id) return action
  if (currentRelation === null) {
    return updateCampaignAction(
      action.id,
      artifactRelationPayload(partial.artifact),
    )
  }
  throw new CampaignActionPartialSuccessError(
    'An active CampaignAction exists, but it is linked to another artifact.',
    partial,
    {
      cause: new Error('CampaignAction relation conflict.'),
      retryable: false,
    },
  )
}

async function retryCampaignActionRegistration(
  partial: PartialCampaignActionCreation,
  workspaceId: string,
  queryClient: QueryClient,
): Promise<CreateActionFromRecommendationResult> {
  const payload = partial.campaignActionPayload

  try {
    const exact = await fetchCampaignActions({
      campaign: payload.campaign,
      recommendation_ref: payload.recommendation_ref,
      action_type: payload.action_type,
      page: 1,
      page_size: 100,
    })
    const existing = exact.results.find((action) =>
      ACTIVE_DUPLICATE_STATUSES.has(action.status),
    )
    const campaignAction = existing
      ? await reconcileExistingAction(existing, partial)
      : await createCampaignAction(payload)

    await Promise.all([
      invalidateBestEffort(
        invalidateArtifactCache(queryClient, workspaceId, partial.artifact),
      ),
      invalidateBestEffort(
        invalidateCampaignActionCache(queryClient, workspaceId, campaignAction),
      ),
    ])
    return {
      campaignAction,
      artifact: partial.artifact,
      recoveredExistingAction: Boolean(existing),
    }
  } catch (cause) {
    if (cause instanceof CampaignActionPartialSuccessError) throw cause
    throw new CampaignActionPartialSuccessError(
      'CampaignAction registration still failed; the existing artifact was not recreated.',
      partial,
      { cause, retryable: true },
    )
  }
}

/** Orchestrate proprietary artifact first, then its persistent CampaignAction. */
export function useCreateActionFromRecommendation(workspaceId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<
    CreateActionFromRecommendationResult,
    unknown,
    CreateActionFromRecommendationMutationInput
  >({
    mutationFn: async (input) => {
      if (!workspaceId) throw new Error('An active workspace is required.')
      if (input.mode === 'retry_campaign_action') {
        return retryCampaignActionRegistration(
          input.partial,
          workspaceId,
          queryClient,
        )
      }

      if (
        input.campaignAction.action_type === 'manual_task' ||
        input.campaignAction.action_type === 'mark_reviewed' ||
        input.campaignAction.action_type === 'dismiss'
      ) {
        const campaignAction = await createCampaignAction(input.campaignAction)
        await invalidateBestEffort(
          invalidateCampaignActionCache(
            queryClient,
            workspaceId,
            campaignAction,
          ),
        )
        return {
          campaignAction,
          artifact: null,
          recoveredExistingAction: false,
        }
      }

      if (!('artifact' in input)) {
        throw new Error('Artifact-backed action input is incomplete.')
      }
      return createTwoStepAction(input, workspaceId, queryClient)
    },
  })
}
