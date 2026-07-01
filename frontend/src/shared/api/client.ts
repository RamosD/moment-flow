/**
 * Central Backend Core HTTP client.
 *
 * This is the ONLY network boundary of the frontend. It targets the Backend
 * Core exclusively (never the Intelligence Engine or Content Renderer) and
 * never sends `X-Internal-Token` — that header is a service-to-service secret
 * and must not exist in the browser.
 *
 * Credentials are injected, not hardcoded: the access token and workspace id
 * are read through provider functions at request time (see ./providers).
 */

import { ENV } from '@/shared/config'

import { NetworkError } from './errors'
import { mapHttpError } from './error-mapping'
import { notifyUnauthorized, readToken, readWorkspaceId } from './providers'
import { appendSafeCustomHeaders } from './security'
import type { RequestOptions, TokenProvider, WorkspaceProvider } from './types'

export interface ApiClientOptions {
  baseUrl: string
  getAuthToken?: TokenProvider
  getWorkspaceId?: WorkspaceProvider
}

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

function buildUrl(
  baseUrl: string,
  path: string,
  params?: RequestOptions['params'],
): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${baseUrl}${normalizedPath}`
  if (!params) return url

  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    search.append(key, String(value))
  }
  const query = search.toString()
  return query ? `${url}?${query}` : url
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const text = await response.text()
  if (!text) return undefined
  const contentType = response.headers.get('Content-Type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return JSON.parse(text)
    } catch {
      return text
    }
  }
  return text
}

export interface ApiClient {
  get<T>(path: string, options?: RequestOptions): Promise<T>
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T>
  delete<T>(path: string, options?: RequestOptions): Promise<T>
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const { baseUrl } = options
  const getAuthToken = options.getAuthToken ?? (() => null)
  const getWorkspaceId = options.getWorkspaceId ?? (() => null)

  async function request<T>(
    method: HttpMethod,
    path: string,
    body: unknown,
    options: RequestOptions = {},
  ): Promise<T> {
    const hasBody = body !== undefined && method !== 'GET'
    const headers = new Headers()
    headers.set('Accept', 'application/json')
    if (hasBody) headers.set('Content-Type', 'application/json')

    if (options.auth !== false) {
      const token = getAuthToken()
      if (token) headers.set('Authorization', `Bearer ${token}`)
    }

    const workspaceId = getWorkspaceId()
    if (workspaceId) headers.set('X-Workspace-ID', workspaceId)

    // Custom headers are merged last; internal-secret headers are stripped.
    appendSafeCustomHeaders(
      options.headers,
      headers,
      ENV.isDev
        ? (headerName) =>
            console.warn(
              `[api] Blocked custom ${headerName}; provider-owned headers cannot be overridden.`,
            )
        : undefined,
    )

    const url = buildUrl(baseUrl, path, options.params)

    let response: Response
    try {
      response = await fetch(url, {
        method,
        headers,
        body: hasBody ? JSON.stringify(body) : undefined,
        signal: options.signal,
      })
    } catch (cause) {
      // Propagate genuine cancellations untouched.
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        throw cause
      }
      throw new NetworkError(
        'Network request failed. The Backend Core may be unreachable.',
        { cause },
      )
    }

    const parsed = await parseBody(response)
    if (!response.ok) {
      // A 401 on an authenticated request means the session token was refused.
      // Login/refresh use `auth: false` and are excluded on purpose.
      if (response.status === 401 && options.auth !== false) {
        notifyUnauthorized()
      }
      throw mapHttpError(response, parsed)
    }
    return parsed as T
  }

  return {
    get: (path, options) => request('GET', path, undefined, options),
    post: (path, body, options) => request('POST', path, body, options),
    patch: (path, body, options) => request('PATCH', path, body, options),
    delete: (path, options) => request('DELETE', path, undefined, options),
  }
}

/**
 * Default singleton client: base URL from env, credentials read through the
 * injectable provider registry. Use this everywhere; call the provider setters
 * (FE-007/FE-008) to wire auth + workspace state.
 */
export const apiClient = createApiClient({
  baseUrl: ENV.apiBaseUrl,
  getAuthToken: readToken,
  getWorkspaceId: readWorkspaceId,
})
