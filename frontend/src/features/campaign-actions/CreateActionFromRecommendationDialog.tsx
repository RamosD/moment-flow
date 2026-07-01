import { useId, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import type { Campaign } from '@/entities/campaign'
import type {
  CreateCampaignActionInput,
  SupportedCampaignActionType,
} from '@/entities/campaign-action'
import { useCreateCampaignAction } from '@/entities/campaign-action'
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

import { SUPPORTED_ACTION_TYPE_OPTIONS } from './action-type-options'
import type { RecommendationActionDraft } from './recommendation-action-draft'
import styles from './campaign-actions.module.css'

interface CreateActionFromRecommendationDialogProps {
  open: boolean
  onClose: () => void
  draft: RecommendationActionDraft
  /** Source campaign — supplies the real required FKs (campaign, artist, track). */
  campaign: Campaign
  workspaceId: string | null
}

/** Join DRF field errors for one backend field into a single message. */
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

/**
 * Confirm-and-create dialog: turns a recommendation draft into a real Backend
 * Core artifact (report / media kit / content-pack request). Pre-fills from the
 * draft, lets the user adjust title/description/type, validates required fields,
 * surfaces per-field 422 errors, and closes on success. No fake persistence —
 * every submit hits a real endpoint via {@link useCreateCampaignAction}.
 */
export function CreateActionFromRecommendationDialog({
  open,
  onClose,
  draft,
  campaign,
  workspaceId,
}: CreateActionFromRecommendationDialogProps) {
  const formId = useId()
  const [title, setTitle] = useState(draft.title)
  const [description, setDescription] = useState(draft.description ?? '')
  const [actionType, setActionType] = useState<SupportedCampaignActionType>(
    draft.suggestedActionType ?? 'report_request',
  )
  const [priority, setPriority] = useState(draft.priority ?? '')
  const [contentPackId, setContentPackId] = useState('')
  const [localError, setLocalError] = useState<{
    title?: string
    contentPack?: string
  }>({})

  const mutation = useCreateCampaignAction(workspaceId, campaign.id)

  const contentPacksQuery = useContentPacks(
    workspaceId,
    actionType === 'content_pack',
  )
  const contentPackOptions = useMemo(
    () =>
      (contentPacksQuery.data ?? []).map((pack) => ({
        value: pack.id,
        label: pack.name,
      })),
    [contentPacksQuery.data],
  )

  const submitError = mutation.error
  const fieldErrors =
    submitError instanceof ValidationError ? submitError.fieldErrors : undefined

  function buildInput(): CreateCampaignActionInput {
    const trimmedTitle = title.trim()
    const metadata: Record<string, string> = {}
    if (description.trim()) metadata.action_description = description.trim()
    if (priority.trim()) metadata.action_priority = priority.trim()
    const base = {
      campaignId: campaign.id,
      recommendationRef: draft.recommendationRef.ref,
      source: draft.source,
      metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
      trackId: campaign.track ?? null,
    }
    switch (actionType) {
      case 'report_request':
        return {
          ...base,
          type: 'report_request',
          title: trimmedTitle,
          artistId: campaign.artist,
        }
      case 'media_kit_request':
        return {
          ...base,
          type: 'media_kit_request',
          title: trimmedTitle,
          artistId: campaign.artist,
        }
      case 'content_pack':
        return {
          ...base,
          type: 'content_pack',
          contentPackId,
          title: trimmedTitle,
          artistId: campaign.artist,
        }
    }
  }

  const busy = mutation.isPending

  function handleClose() {
    if (busy) return
    mutation.reset()
    setLocalError({})
    onClose()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const nextLocal: { title?: string; contentPack?: string } = {}
    if (!title.trim()) nextLocal.title = 'Title is required.'
    if (actionType === 'content_pack' && !contentPackId) {
      nextLocal.contentPack = 'Choose a content pack.'
    }
    setLocalError(nextLocal)
    if (Object.keys(nextLocal).length > 0) return

    mutation.mutate(buildInput(), {
      onSuccess: () => {
        mutation.reset()
        onClose()
      },
    })
  }

  // Show a general alert for any error that isn't already surfaced inline on a
  // visible field — so a 422 on a derived field (artist/campaign) is never silent.
  const visibleFieldErrored = Boolean(
    fieldError(fieldErrors, 'title') || fieldError(fieldErrors, 'content_pack'),
  )
  const generalError =
    submitError && !visibleFieldErrored ? resolveErrorPreset(submitError) : null

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Create action"
      description="Turn this recommendation into a tracked artifact in the Backend Core."
    >
      <form id={formId} className={styles.form} onSubmit={handleSubmit}>
        {generalError && (
          <Alert variant="danger" title={generalError.title}>
            {generalError.description}
          </Alert>
        )}

        <FormField
          label="Action type"
          htmlFor={`${formId}-type`}
          required
          hint="Only types backed by the Backend Core are listed."
        >
          <Select
            id={`${formId}-type`}
            options={SUPPORTED_ACTION_TYPE_OPTIONS}
            value={actionType}
            disabled={busy}
            onChange={(event) =>
              setActionType(event.target.value as SupportedCampaignActionType)
            }
          />
        </FormField>

        <FormField
          label="Title"
          htmlFor={`${formId}-title`}
          required
          error={localError.title ?? fieldError(fieldErrors, 'title')}
        >
          <Input
            id={`${formId}-title`}
            value={title}
            disabled={busy}
            onChange={(event) => setTitle(event.target.value)}
          />
        </FormField>

        {actionType === 'content_pack' && (
          <FormField
            label="Content pack"
            htmlFor={`${formId}-pack`}
            required
            error={
              localError.contentPack ?? fieldError(fieldErrors, 'content_pack')
            }
            hint={
              contentPacksQuery.isError
                ? 'Could not load content packs. Try again shortly.'
                : undefined
            }
          >
            <Select
              id={`${formId}-pack`}
              options={contentPackOptions}
              placeholder={
                contentPacksQuery.isPending
                  ? 'Loading content packs…'
                  : contentPackOptions.length === 0
                    ? 'No content packs available'
                    : 'Select a content pack'
              }
              value={contentPackId}
              disabled={busy || contentPacksQuery.isPending}
              onChange={(event) => setContentPackId(event.target.value)}
            />
          </FormField>
        )}

        <FormField
          label="Description"
          htmlFor={`${formId}-description`}
          hint="Optional. Stored with the artifact."
        >
          <Textarea
            id={`${formId}-description`}
            value={description}
            disabled={busy}
            onChange={(event) => setDescription(event.target.value)}
          />
        </FormField>

        <FormField
          label="Priority"
          htmlFor={`${formId}-priority`}
          hint="Optional. Recorded in metadata (not a backend status)."
        >
          <Input
            id={`${formId}-priority`}
            value={priority}
            disabled={busy}
            onChange={(event) => setPriority(event.target.value)}
          />
        </FormField>

        <div className={styles.formActions}>
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={busy}
          >
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Creating…' : 'Create action'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
