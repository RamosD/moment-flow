/**
 * Tenant selection belongs to the central workspace header provider. Remove a
 * workspace field defensively even when an untyped caller supplied one.
 */
export function sanitizeCampaignActionWritePayload<T extends object>(
  payload: T,
): T {
  const body = { ...payload } as T & { workspace?: unknown }
  delete body.workspace
  return body
}
