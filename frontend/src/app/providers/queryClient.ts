import { QueryCache, QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/shared/api'
import { ENV } from '@/shared/config'

/**
 * Conservative retry policy: never retry client errors (4xx) — they will not
 * fix themselves and a 401/403/404/422 should surface immediately. Retry other
 * failures (5xx, network) up to twice.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
    return false
  }
  return failureCount < 2
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      staleTime: 30_000, // 30s — avoid refetch storms during navigation.
      gcTime: 5 * 60_000, // 5min cache retention.
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      if (!ENV.isDev) return
      // ApiError never carries tokens or request headers, so a short summary
      // is safe to log. Never log the token, Authorization header or full URL.
      const summary =
        error instanceof ApiError
          ? `status=${error.status} code=${error.code ?? '-'}`
          : 'unknown error'
      console.error(`[query] request failed (${summary}): ${error.message}`)
    },
  }),
})
