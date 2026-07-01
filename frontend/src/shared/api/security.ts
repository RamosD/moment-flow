/** Header that must never leave the browser frontend. */
export const INTERNAL_TOKEN_HEADER = 'x-internal-token'

const PROVIDER_OWNED_HEADERS = new Set([
  INTERNAL_TOKEN_HEADER,
  'authorization',
  'x-workspace-id',
])

/** Merge caller headers while dropping the service-to-service credential. */
export function appendSafeCustomHeaders(
  customHeaders: Record<string, string> | undefined,
  target: Headers,
  onBlockedProviderHeader?: (headerName: string) => void,
): void {
  if (!customHeaders) return
  for (const [key, value] of Object.entries(customHeaders)) {
    if (PROVIDER_OWNED_HEADERS.has(key.toLowerCase())) {
      onBlockedProviderHeader?.(key)
      continue
    }
    target.set(key, value)
  }
}
