import { apiClient } from '@/shared/api'

import type {
  ContentPackRequest,
  CreateContentPackRequestPayload,
} from './model'

/** Create the proprietary artefact; workspace is injected by apiClient. */
export function createContentPackRequest(
  payload: CreateContentPackRequestPayload,
): Promise<ContentPackRequest> {
  return apiClient.post<ContentPackRequest>('/content-pack-requests/', payload)
}
