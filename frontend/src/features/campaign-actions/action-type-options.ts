/**
 * `Select` options for choosing a campaign action type, derived from the
 * single source of truth (`CAMPAIGN_ACTION_CAPABILITIES`) so the UI can never
 * drift from what the Backend Core actually supports.
 */

import type { SelectOption } from '@/shared/ui'
import {
  CAMPAIGN_ACTION_CAPABILITIES,
  campaignActionTypeLabel,
  SUPPORTED_CAMPAIGN_ACTION_TYPES,
} from '@/entities/campaign-action'
import type { CampaignActionType } from '@/entities/campaign-action'

const ALL_ACTION_TYPES = Object.keys(
  CAMPAIGN_ACTION_CAPABILITIES,
) as CampaignActionType[]

/** Every action type, with unsupported ones disabled (honest, never hidden). */
export const ACTION_TYPE_OPTIONS: SelectOption[] = ALL_ACTION_TYPES.map(
  (type) => {
    const capability = CAMPAIGN_ACTION_CAPABILITIES[type]
    return {
      value: type,
      label: capability.supported
        ? campaignActionTypeLabel(type)
        : `${campaignActionTypeLabel(type)} (unavailable)`,
      disabled: !capability.supported,
    }
  },
)

/** Only the action types that can actually be created today. */
export const SUPPORTED_ACTION_TYPE_OPTIONS: SelectOption[] =
  SUPPORTED_CAMPAIGN_ACTION_TYPES.map((type) => ({
    value: type,
    label: campaignActionTypeLabel(type),
  }))
