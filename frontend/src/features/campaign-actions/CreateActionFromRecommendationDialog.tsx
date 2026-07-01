import { useId, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type { Campaign } from '@/entities/campaign'
import type { CampaignActionPriority } from '@/entities/campaign-action'
import {
  campaignActionKeys,
  campaignActionTypeLabel,
  useAllCampaignActionsByRecommendationType,
} from '@/entities/campaign-action'
import { useContentPacks } from '@/entities/content-pack'
import { ValidationError } from '@/shared/api'
import type { FieldErrors } from '@/shared/api'
import {
  Alert,
  Button,
  Dialog,
  FormField,
  Input,
  resolveErrorPreset,
  Select,
  Textarea,
} from '@/shared/ui'

import {
  CAMPAIGN_ACTION_PRIORITY_OPTIONS,
  RECOMMENDATION_CREATE_ACTION_TYPE_OPTIONS,
} from './action-type-options'
import type { RecommendationCreateActionType } from './action-type-options'
import type { RecommendationActionDraft } from './recommendation-action-draft'
import {
  findActiveRecommendationAction,
  matchRecommendationActions,
} from './recommendation-action-match'
import { RecommendationActionState } from './RecommendationActionState'
import {
  CampaignActionPartialSuccessError,
  useCreateActionFromRecommendation,
} from './useCreateActionFromRecommendation'
import type { CreateActionFromRecommendationMutationInput } from './useCreateActionFromRecommendation'
import styles from './campaign-actions.module.css'

interface CreateActionFromRecommendationDialogProps {
  open: boolean
  onClose: () => void
  draft: RecommendationActionDraft
  campaign: Campaign
  workspaceId: string | null
}

const NON_VISIBLE_ERROR_FIELDS = [
  'recommendation_ref',
  'recommendation_snapshot',
  'related_report',
  'related_media_kit',
  'related_content_pack_request',
  'dismiss_reason',
] as const

function fieldError(
  fieldErrors: FieldErrors | undefined,
  ...keys: string[]
): string | undefined {
  if (!fieldErrors) return undefined
  for (const key of keys) {
    const messages = fieldErrors[key]
    if (messages && messages.length > 0) return messages.join(' ')
  }
  return undefined
}

function nonVisibleFieldError(fieldErrors: FieldErrors | undefined) {
  if (!fieldErrors) return undefined
  const messages = NON_VISIBLE_ERROR_FIELDS.flatMap((field) =>
    (fieldErrors[field] ?? []).map((message) => `${field}: ${message}`),
  )
  return messages.length > 0 ? messages.join(' ') : undefined
}

function unwrapMutationError(error: unknown): unknown {
  return error instanceof CampaignActionPartialSuccessError
    ? error.cause
    : error
}

function isDuplicateError(error: unknown): boolean {
  const unwrapped = unwrapMutationError(error)
  if (!(unwrapped instanceof ValidationError)) return false
  return (unwrapped.fieldErrors?.recommendation_ref ?? []).some((message) =>
    /already exists|active action/i.test(message),
  )
}

/** Create an artifact (when required) and then its persistent CampaignAction. */
export function CreateActionFromRecommendationDialog({
  open,
  onClose,
  draft,
  campaign,
  workspaceId,
}: CreateActionFromRecommendationDialogProps) {
  const formId = useId()
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(draft.title)
  const [description, setDescription] = useState(draft.description ?? '')
  const [actionType, setActionType] = useState<RecommendationCreateActionType>(
    draft.suggestedActionType ?? 'manual_task',
  )
  const [priority, setPriority] =
    useState<CampaignActionPriority>(draft.priority)
  const [contentPackId, setContentPackId] = useState('')
  const [localErrors, setLocalErrors] = useState<{
    title?: string
    content_pack?: string
  }>({})

  const mutation = useCreateActionFromRecommendation(workspaceId)
  const exactTypeQuery = useAllCampaignActionsByRecommendationType(
    workspaceId,
    campaign.id,
    draft.recommendationRef.ref,
    actionType,
  )
  const exactTypeActions = matchRecommendationActions(
    draft,
    exactTypeQuery.data?.results,
  )
  const activeAction = findActiveRecommendationAction(
    exactTypeActions,
    actionType,
  )
  const partialError =
    mutation.error instanceof CampaignActionPartialSuccessError
      ? mutation.error
      : null
  const effectiveSubmitError = unwrapMutationError(mutation.error)
  const fieldErrors =
    effectiveSubmitError instanceof ValidationError
      ? effectiveSubmitError.fieldErrors
      : undefined
  const duplicateError = isDuplicateError(mutation.error)
  const derivedFieldError = nonVisibleFieldError(fieldErrors)
  const generalError =
    effectiveSubmitError &&
    !partialError &&
    !duplicateError &&
    !derivedFieldError &&
    !fieldError(
      fieldErrors,
      'title',
      'description',
      'priority',
      'content_pack',
    )
      ? resolveErrorPreset(effectiveSubmitError)
      : null
  const busy = mutation.isPending
  const locked = busy || Boolean(partialError)
  const exactLookupReady = !exactTypeQuery.isPending && !exactTypeQuery.isError

  const contentPacksQuery = useContentPacks(
    workspaceId,
    actionType === 'content_pack' && !locked,
  )
  const contentPackOptions = useMemo(
    () =>
      (contentPacksQuery.data ?? []).map((pack) => ({
        value: pack.id,
        label: pack.name,
      })),
    [contentPacksQuery.data],
  )

  function buildInput(): CreateActionFromRecommendationMutationInput {
    const campaignActionBase = {
      campaign: campaign.id,
      recommendation_ref: draft.recommendationRef.ref,
      recommendation_snapshot: draft.recommendationSnapshot,
      title: title.trim(),
      description: description.trim(),
      priority,
      source: draft.source,
    }

    switch (actionType) {
      case 'manual_task':
        return {
          mode: 'create',
          campaignAction: {
            ...campaignActionBase,
            action_type: 'manual_task',
          },
        }
      case 'content_pack':
        return {
          mode: 'create',
          campaignAction: {
            ...campaignActionBase,
            action_type: 'content_pack',
          },
          artifact: {
            content_pack: contentPackId,
            artist: campaign.artist,
            track: campaign.track ?? null,
          },
        }
      case 'report_request':
        return {
          mode: 'create',
          campaignAction: {
            ...campaignActionBase,
            action_type: 'report_request',
          },
          artifact: {
            artist: campaign.artist,
            track: campaign.track ?? null,
          },
        }
      case 'media_kit_request':
        return {
          mode: 'create',
          campaignAction: {
            ...campaignActionBase,
            action_type: 'media_kit_request',
          },
          artifact: {
            artist: campaign.artist,
            track: campaign.track ?? null,
          },
        }
    }
  }

  function handleClose() {
    if (busy || partialError?.retryable) return
    mutation.reset()
    setLocalErrors({})
    onClose()
  }

  async function refreshDuplicate(error: unknown) {
    if (!isDuplicateError(error)) return
    await Promise.all([
      exactTypeQuery.refetch(),
      queryClient.invalidateQueries({
        queryKey: campaignActionKeys.recommendationRoot(
          workspaceId,
          campaign.id,
          draft.recommendationRef.ref,
        ),
      }),
    ])
  }

  function handleSuccess() {
    mutation.reset()
    onClose()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || partialError || !exactLookupReady || activeAction) return

    const nextErrors: typeof localErrors = {}
    if (!title.trim()) nextErrors.title = 'Title is required.'
    if (actionType === 'content_pack' && !contentPackId) {
      nextErrors.content_pack = 'Choose a content pack.'
    }
    setLocalErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    mutation.mutate(buildInput(), {
      onError: (error) => void refreshDuplicate(error),
      onSuccess: handleSuccess,
    })
  }

  function handleRetryCampaignAction() {
    if (!partialError?.retryable || busy) return
    mutation.mutate(
      {
        mode: 'retry_campaign_action',
        partial: partialError.partial,
      },
      {
        onError: (error) => void refreshDuplicate(error),
        onSuccess: handleSuccess,
      },
    )
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Create campaign action"
      description="Artifact-backed actions create the artifact first, then register a persistent CampaignAction with the related id."
    >
      <form id={formId} className={styles.form} onSubmit={handleSubmit}>
        {partialError && (
          <Alert variant="warning" title="Artifact created; action not registered">
            <p>
              {partialError.message} No artifact rollback or automatic artifact
              retry was attempted.
            </p>
            {derivedFieldError && <p>{derivedFieldError}</p>}
            <p className={styles.artifactReference}>
              {partialError.partial.artifact.kind}:{' '}
              {partialError.partial.artifact.id}
            </p>
            {partialError.retryable ? (
              <div className={styles.partialActions}>
                <Button
                  type="button"
                  variant="warning"
                  size="sm"
                  disabled={busy}
                  onClick={handleRetryCampaignAction}
                >
                  {busy ? 'Checking…' : 'Retry CampaignAction only'}
                </Button>
              </div>
            ) : (
              <p>Retry is disabled because the artifact scope/relation conflicts.</p>
            )}
          </Alert>
        )}
        {duplicateError && !partialError && (
          <Alert variant="warning" title="Action already exists">
            An active action of this type already exists for this recommendation.
            The exact CampaignAction state has been refreshed.
          </Alert>
        )}
        {exactTypeQuery.isError && !partialError && (
          <Alert variant="danger" title="Could not verify existing action">
            Creation is disabled until the exact recommendation and action type
            lookup succeeds.
          </Alert>
        )}
        {activeAction && !partialError && (
          <Alert
            variant="info"
            title={`Active ${campaignActionTypeLabel(actionType)} action exists`}
          >
            <p>
              Only this action type is blocked. Choose another type, or create a
              new one after this action becomes failed, dismissed or cancelled.
            </p>
            <RecommendationActionState actions={[activeAction]} totalCount={1} />
          </Alert>
        )}
        {derivedFieldError && !duplicateError && !partialError && (
          <Alert variant="danger" title="Campaign action could not be created">
            {derivedFieldError}
          </Alert>
        )}
        {generalError && (
          <Alert variant="danger" title={generalError.title}>
            {generalError.description}
          </Alert>
        )}

        <FormField
          label="Action type"
          htmlFor={`${formId}-type`}
          required
          hint="Mark reviewed and dismiss are handled by their dedicated decision flows."
        >
          <Select
            id={`${formId}-type`}
            options={RECOMMENDATION_CREATE_ACTION_TYPE_OPTIONS}
            value={actionType}
            disabled={locked}
            onChange={(event) => {
              mutation.reset()
              setActionType(
                event.target.value as RecommendationCreateActionType,
              )
            }}
          />
        </FormField>

        <FormField
          label="Title"
          htmlFor={`${formId}-title`}
          required
          error={localErrors.title ?? fieldError(fieldErrors, 'title')}
        >
          <Input
            id={`${formId}-title`}
            value={title}
            disabled={locked}
            onChange={(event) => setTitle(event.target.value)}
          />
        </FormField>

        {actionType === 'content_pack' && (
          <FormField
            label="Content pack"
            htmlFor={`${formId}-content-pack`}
            required
            error={
              localErrors.content_pack ?? fieldError(fieldErrors, 'content_pack')
            }
            hint={
              contentPacksQuery.isError
                ? 'Could not load content packs. Try again shortly.'
                : undefined
            }
          >
            <Select
              id={`${formId}-content-pack`}
              options={contentPackOptions}
              placeholder={
                contentPacksQuery.isPending
                  ? 'Loading content packs…'
                  : contentPackOptions.length === 0
                    ? 'No content packs available'
                    : 'Select a content pack'
              }
              value={contentPackId}
              disabled={locked || contentPacksQuery.isPending}
              onChange={(event) => setContentPackId(event.target.value)}
            />
          </FormField>
        )}

        <FormField
          label="Description"
          htmlFor={`${formId}-description`}
          hint="Optional. Stored as a top-level CampaignAction field."
          error={fieldError(fieldErrors, 'description')}
        >
          <Textarea
            id={`${formId}-description`}
            value={description}
            disabled={locked}
            onChange={(event) => setDescription(event.target.value)}
          />
        </FormField>

        <FormField
          label="Priority"
          htmlFor={`${formId}-priority`}
          required
          hint="Stored as a top-level CampaignAction field."
          error={fieldError(fieldErrors, 'priority')}
        >
          <Select
            id={`${formId}-priority`}
            options={CAMPAIGN_ACTION_PRIORITY_OPTIONS}
            value={priority}
            disabled={locked}
            onChange={(event) =>
              setPriority(event.target.value as CampaignActionPriority)
            }
          />
        </FormField>

        <Alert variant="info" title="Recommendation context">
          Source, recommendation_ref and the safe recommendation_snapshot are
          recorded automatically as canonical CampaignAction fields.
        </Alert>

        <div className={styles.formActions}>
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={busy || Boolean(partialError?.retryable)}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={
              locked ||
              (actionType === 'content_pack' &&
                contentPacksQuery.isPending) ||
              !exactLookupReady ||
              Boolean(activeAction)
            }
          >
            {busy
              ? 'Creating…'
              : activeAction
                ? 'Active action exists'
                : exactTypeQuery.isPending
                  ? 'Checking existing action…'
                  : 'Create campaign action'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
